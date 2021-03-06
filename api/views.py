# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=duplicate-except,attribute-defined-outside-init,too-many-lines

from django.db import transaction
from django.contrib.auth.models import User
from django_filters import rest_framework as drf_filters

import rest_framework
from rest_framework import routers
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.authtoken.views import ObtainAuthToken

from adcm.settings import ADCM_VERSION
import cm.job
import cm.api
import cm.stack
import cm.status_api
import cm.config as config
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import HostProvider, Host, ADCM, Action
from cm.models import JobLog, TaskLog, Upgrade
from cm.models import ObjectConfig, ConfigLog, UserProfile
from cm.logger import log   # pylint: disable=unused-import

import api.serializers
import api.cluster_serial
from api.serializers import check_obj, filter_actions, get_config_version
from api.api_views import create, update
from api.api_views import ListView, PageView, PageViewAdd
from api.api_views import DetailViewRO, DetailViewDelete, ActionFilter


@transaction.atomic
def delete_user(username):
    user = check_obj(User, {'username': username}, 'USER_NOT_FOUND')
    try:
        profile = UserProfile.objects.get(login=user.username)
        profile.delete()
    except UserProfile.DoesNotExist:
        pass
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


class APIRoot(routers.APIRootView):
    """
    Arenadata Chapel API
    """
    permission_classes = (rest_framework.permissions.AllowAny,)
    api_root_dict = {
        'adcm': 'adcm',
        'cluster': 'cluster',
        'profile': 'profile-list',
        'provider': 'provider',
        'host': 'host',
        'job': 'job',
        'stack': 'stack',
        'stats': 'stats',
        'task': 'task',
        'token': 'token',
        'user': 'user-list',
        'info': 'adcm-info',
    }


class NameConverter:
    regex = cm.stack.NAME_REGEX

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


class GetAuthToken(ObtainAuthToken, GenericAPIView):
    authentication_classes = (rest_framework.authentication.TokenAuthentication,)
    permission_classes = (rest_framework.permissions.AllowAny,)
    serializer_class = api.serializers.AuthSerializer

    def post(self, *args, **kwargs):   # pylint: disable=arguments-differ,useless-super-delegation
        """
        Provide authentication token

        HTTP header for authorization:

        ```
        Authorization: Token XXXXX
        ```
        """
        return super(GetAuthToken, self).post(*args, **kwargs)


class ADCMInfo(GenericAPIView):
    permission_classes = (rest_framework.permissions.AllowAny,)
    serializer_class = api.serializers.EmptySerializer

    def get(self, request):
        """
        General info about ADCM
        """
        return Response({
            'adcm_version': ADCM_VERSION,
            'google_oauth': cm.api.has_google_oauth()
        })


class UserList(PageViewAdd):
    """
    get:
    List all existing users

    post:
    Create new user
    """
    queryset = User.objects.all()
    serializer_class = api.serializers.UserSerializer
    ordering_fields = ('username',)


class UserDetail(GenericAPIView):
    queryset = User.objects.all()
    serializer_class = api.serializers.UserSerializer

    def get(self, request, username):
        """
        show user
        """
        user = check_obj(User, {'username': username}, 'USER_NOT_FOUND')
        serializer = self.serializer_class(user, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, username):
        """
        delete user and profile
        """
        return delete_user(username)


class UserPasswd(GenericAPIView):
    queryset = User.objects.all()
    serializer_class = api.serializers.UserPasswdSerializer

    def patch(self, request, username):
        """
        Change user password
        """
        user = check_obj(User, {'username': username}, 'USER_NOT_FOUND')
        serializer = self.serializer_class(user, data=request.data, context={'request': request})
        return update(serializer)


class ProfileList(PageViewAdd):
    """
    get:
    List all existing user's profiles

    post:
    Create new user profile
    """
    queryset = UserProfile.objects.all()
    serializer_class = api.serializers.ProfileSerializer
    ordering_fields = ('username',)


class ProfileDetail(DetailViewRO):
    """
    get:
    Show user profile
    """
    queryset = UserProfile.objects.all()
    serializer_class = api.serializers.ProfileDetailSerializer
    lookup_field = 'login'
    lookup_url_kwarg = 'username'
    error_code = 'USER_NOT_FOUND'

    def get_object(self):
        login = self.kwargs['username']
        try:
            up = UserProfile.objects.get(login=login)
        except UserProfile.DoesNotExist:
            try:
                user = User.objects.get(username=login)
                up = UserProfile.objects.create(login=user.username)
                up.save()
            except User.DoesNotExist:
                raise AdcmApiEx('USER_NOT_FOUND')
        return up

    def patch(self, request, *args, **kwargs):
        """
        Edit user profile
        """
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)

    def delete(self, request, username):
        """
        delete user and profile
        """
        return delete_user(username)


class AdcmList(ListView):
    """
    get:
    List adcm object
    """
    queryset = ADCM.objects.all()
    serializer_class = api.serializers.AdcmSerializer
    serializer_class_ui = api.serializers.AdcmDetailSerializer


class AdcmDetail(DetailViewRO):
    """
    get:
    Show adcm object
    """
    queryset = ADCM.objects.all()
    serializer_class = api.serializers.AdcmDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'adcm_id'
    error_code = 'ADCM_NOT_FOUND'


class AdcmConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.AdcmConfigSerializer

    def get(self, request, adcm_id):   # pylint: disable=arguments-differ
        """
        Show current config for a adcm object
        """
        check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(
            obj, context={'request': request, 'adcm_id': adcm_id}
        )
        return Response(serializer.data)


class AdcmConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.AdcmConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, adcm_id):
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'adcm': adcm}, 'CONFIG_NOT_FOUND')
        return (adcm, oc, self.get_queryset().get(obj_ref=oc, id=oc.current))

    def get(self, request, adcm_id):   # pylint: disable=arguments-differ
        """
        Show history of config of an adcm object
        """
        _, oc, _ = self.get_obj(adcm_id)
        obj = self.get_queryset().filter(obj_ref=oc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, adcm_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(adcm_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class AdcmConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, adcm_id, version):   # pylint: disable=arguments-differ
        """
        Show config for a specified version of adcm object.

        """
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'adcm': adcm}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(adcm, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ADCMActionList(ListView):
    queryset = Action.objects.filter(prototype__type='adcm')
    serializer_class = api.serializers.ADCMActionList
    serializer_class_ui = api.serializers.ProviderActionDetail
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, adcm_id):   # pylint: disable=arguments-differ
        """
        List all actions of an ADCM
        """
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        obj = filter_actions(adcm, self.filter_queryset(
            self.get_queryset().filter(prototype=adcm.prototype)
        ))
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            obj, many=True, context={'request': request, 'adcm_id': adcm_id}
        )
        return Response(serializer.data)


class ADCMAction(GenericAPIView):
    queryset = Action.objects.filter(prototype__type='adcm')
    serializer_class = api.serializers.ADCMActionDetail

    def get(self, request, adcm_id, action_id):
        """
        Show specified action of an ADCM
        """
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        obj = filter_actions(adcm, self.get_queryset().filter(prototype=adcm.prototype))
        obj = check_obj(
            Action,
            {'prototype': adcm.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(
            obj, context={'request': request, 'adcm_id': adcm_id}
        )
        return Response(serializer.data)


class ADCMTask(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.TaskRunSerializer

    def post(self, request, adcm_id, action_id):
        """
        Ran specified action of a specified host provider
        """
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        check_obj(
            Action,
            {'prototype': adcm.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action_id=int(action_id), selector={'adcm': adcm.id})


class ProviderList(PageViewAdd):
    """
    get:
    List all host providers

    post:
    Create new host provider
    """
    queryset = HostProvider.objects.all()
    serializer_class = api.serializers.ProviderSerializer
    serializer_class_ui = api.serializers.ProviderUISerializer
    serializer_class_post = api.serializers.ProviderDetailSerializer
    filterset_fields = ('name', 'prototype_id')
    ordering_fields = ('name', 'state', 'prototype__display_name', 'prototype__version_order')


class ProviderDetail(DetailViewDelete):
    """
    get:
    Show host provider
    """
    queryset = HostProvider.objects.all()
    serializer_class = api.serializers.ProviderDetailSerializer
    serializer_class_ui = api.serializers.ProviderUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'provider_id'
    error_code = 'PROVIDER_NOT_FOUND'

    def delete(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        Remove host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        try:
            cm.api.delete_host_provider(provider)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderHostList(PageView):
    """
    post:
    Create new host
    """
    queryset = Host.objects.all()
    serializer_class = api.serializers.ProviderHostSerializer
    serializer_class_ui = api.serializers.HostUISerializer
    filterset_fields = ('fqdn', 'cluster_id')
    ordering_fields = (
        'fqdn', 'state', 'prototype__display_name', 'prototype__version_order'
    )

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        List all hosts of specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = self.filter_queryset(self.get_queryset().filter(provider=provider))
        return self.get_page(obj, request)

    def post(self, request, provider_id):
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            data=request.data, context={'request': request, 'provider': provider}
        )
        return create(serializer, provider=provider)


class HostFilter(drf_filters.FilterSet):
    cluster_is_null = drf_filters.BooleanFilter(field_name='cluster_id', lookup_expr='isnull')
    provider_is_null = drf_filters.BooleanFilter(field_name='provider_id', lookup_expr='isnull')

    class Meta:
        model = Host
        fields = ['cluster_id', 'prototype_id', 'provider_id', 'fqdn']


class HostList(PageViewAdd):
    """
    get:
    List all hosts

    post:
    Create new host
    """
    queryset = Host.objects.all()
    serializer_class = api.serializers.HostSerializer
    serializer_class_ui = api.serializers.HostUISerializer
    serializer_class_post = api.serializers.HostDetailSerializer
    filterset_class = HostFilter
    filterset_fields = (
        'cluster_id', 'prototype_id', 'provider_id', 'fqdn', 'cluster_is_null', 'provider_is_null'
    )   # just for documentation
    ordering_fields = (
        'fqdn', 'state', 'provider__name', 'cluster__name',
        'prototype__display_name', 'prototype__version_order',
    )


class HostDetail(DetailViewDelete):
    """
    get:
    Show host
    """
    queryset = Host.objects.all()
    serializer_class = api.serializers.HostDetailSerializer
    serializer_class_ui = api.serializers.HostUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'host_id'
    error_code = 'HOST_NOT_FOUND'

    def delete(self, request, host_id):   # pylint: disable=arguments-differ
        """
        Remove host (and all corresponding host services:components)
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        try:
            cm.api.delete_host(host)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code)
        return Response(status=status.HTTP_204_NO_CONTENT)


class Stats(GenericAPIView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.StatsSerializer

    def get(self, request):
        """
        Statistics
        """
        obj = JobLog(id=1)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class JobStats(GenericAPIView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.EmptySerializer

    def get(self, request, job_id):
        """
        Show jobs stats
        """
        jobs = self.get_queryset().filter(id__gt=job_id)
        data = {
            config.Job.FAILED: jobs.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: jobs.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: jobs.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)


class TaskStats(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.EmptySerializer

    def get(self, request, task_id):
        """
        Show tasks stats
        """
        tasks = self.get_queryset().filter(id__gt=task_id)
        data = {
            config.Job.FAILED: tasks.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: tasks.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: tasks.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)


class JobList(PageView):
    """
    get:
    List all jobs
    """
    queryset = JobLog.objects.order_by('-id')
    serializer_class = api.serializers.JobListSerializer
    serializer_class_ui = api.serializers.JobSerializer
    filterset_fields = ('action_id', 'task_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')


class JobDetail(GenericAPIView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.JobSerializer

    def get(self, request, job_id):
        """
        Show job
        """
        job = check_obj(JobLog, job_id, 'JOB_NOT_FOUND')
        job.log_dir = config.LOG_DIR
        logs = cm.job.get_log_files(job)
        for lg in logs:
            lg['url'] = reverse(
                'log-file', kwargs={
                    'job_id': job.id,
                    'level': lg['level'],
                    'tag': lg['tag'],
                    'log_type': lg['type'],
                }, request=request
            )
        job.log_files = logs
        serializer = self.serializer_class(job, data=request.data, context={'request': request})
        serializer.is_valid()
        return Response(serializer.data)


class LogFile(GenericAPIView):
    queryset = JobLog.objects.all()
    serializer_class = api.serializers.LogSerializer

    def get(self, request, job_id, tag, level, log_type):
        """
        Show log file
        """
        lf = JobLog()
        try:
            lf.content = cm.job.read_log(job_id, tag, level, log_type)
            lf.type = log_type
            lf.tag = tag
            lf.level = level
            serializer = self.serializer_class(lf, context={'request': request})
            return Response(serializer.data)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code)


class Task(PageView):
    """
    get:
    List all tasks
    """
    queryset = TaskLog.objects.order_by('-id')
    serializer_class = api.serializers.TaskListSerializer
    serializer_class_ui = api.serializers.TaskSerializer
    post_serializer = api.serializers.TaskPostSerializer
    filterset_fields = ('action_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')

    def post(self, request):
        """
        Create and run new task
        Return handler to new task
        """
        serializer = self.post_serializer(data=request.data, context={'request': request})
        return create(serializer)


class TaskDetail(DetailViewRO):
    """
    get:
    Show task
    """
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.TaskSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'task_id'
    error_code = 'TASK_NOT_FOUND'

    def get_object(self):
        task = super().get_object()
        task.jobs = JobLog.objects.filter(task_id=task.id)
        return task


class TaskReStart(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.TaskRunSerializer

    def post(self, request, task_id):
        task = check_obj(TaskLog, task_id, 'TASK_NOT_FOUND')
        try:
            cm.job.restart_task(task)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code)
        return Response(status.HTTP_200_OK)


class ProviderConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ProviderConfigSerializer

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        Show current config for a specified host provider
        """
        check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(
            obj, context={'request': request, 'provider_id': provider_id}
        )
        return Response(serializer.data)


class ProviderConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ProviderConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, provider_id):
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        return (provider, cc, self.get_queryset().get(obj_ref=cc, id=cc.current))

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        Show history of config of a specified host provider
        """
        _, cc, _ = self.get_obj(provider_id)
        obj = self.get_queryset().filter(obj_ref=cc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, provider_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(provider_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class ProviderConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, provider_id, version):   # pylint: disable=arguments-differ
        """
        Show config for a specified version and host provider.

        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(provider, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ProviderConfigRestore(GenericAPIView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfigRestore

    def patch(self, request, provider_id, version):
        """
        Restore config of specified version of a specified host provider.
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        try:
            obj = self.get_queryset().get(obj_ref=cc, id=version)
        except ConfigLog.DoesNotExist:
            raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)


class ProviderActionList(ListView):
    queryset = Action.objects.filter(prototype__type='provider')
    serializer_class = api.serializers.ProviderActionList
    serializer_class_ui = api.serializers.ProviderActionDetail
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        List all actions of a specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = filter_actions(provider, self.filter_queryset(
            self.get_queryset().filter(prototype=provider.prototype)
        ))
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            obj, many=True, context={'request': request, 'provider_id': provider_id}
        )
        return Response(serializer.data)


class ProviderAction(GenericAPIView):
    queryset = Action.objects.filter(prototype__type='provider')
    serializer_class = api.serializers.ProviderActionDetail

    def get(self, request, provider_id, action_id):
        """
        Show specified action of a specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = filter_actions(provider, self.get_queryset().filter(prototype=provider.prototype))
        obj = check_obj(
            Action,
            {'prototype': provider.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(
            obj, context={'request': request, 'provider_id': provider_id}
        )
        return Response(serializer.data)


class ProviderTask(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.TaskRunSerializer

    def post(self, request, provider_id, action_id):
        """
        Ran specified action of a specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        check_obj(
            Action,
            {'prototype': provider.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action_id=int(action_id), selector={'provider': provider.id})


class ProviderUpgrade(PageView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeProviderSerializer

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = cm.upgrade.get_upgrade(provider, self.get_ordering(request, self.queryset, self))
        serializer = self.serializer_class(obj, many=True, context={
            'provider_id': provider.id, 'request': request
        })
        return Response(serializer.data)


class ProviderUpgradeDetail(ListView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeProviderSerializer

    def get(self, request, provider_id, upgrade_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = self.get_queryset().get(id=upgrade_id)
        serializer = self.serializer_class(obj, context={
            'provider_id': provider.id, 'request': request
        })
        return Response(serializer.data)


class DoProviderUpgrade(GenericAPIView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.DoUpgradeSerializer

    def post(self, request, provider_id, upgrade_id):
        """
        Do upgrade specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, upgrade_id=int(upgrade_id), obj=provider)


class HostActionList(ListView):
    queryset = Action.objects.filter(prototype__type='host')
    serializer_class = api.serializers.HostActionList
    serializer_class_ui = api.serializers.HostActionDetail
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, host_id):   # pylint: disable=arguments-differ
        """
        List all actions of a specified host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        obj = filter_actions(host, self.filter_queryset(
            self.get_queryset().filter(prototype=host.prototype)
        ))
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            obj, many=True, context={'request': request, 'host_id': host_id}
        )
        return Response(serializer.data)


class HostAction(GenericAPIView):
    queryset = Action.objects.filter(prototype__type='host')
    serializer_class = api.serializers.HostActionDetail

    def get(self, request, host_id, action_id):
        """
        Show specified action of a specified host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        obj = check_obj(
            Action,
            {'prototype': host.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(
            obj, context={'request': request, 'host_id': host_id}
        )
        return Response(serializer.data)


class HostTask(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = api.serializers.TaskRunSerializer

    def post(self, request, host_id, action_id):
        """
        Ran specified action of a specified host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        check_obj(
            Action,
            {'prototype': host.prototype, 'id': action_id},
            'ACTION_NOT_FOUND'
        )
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action_id=int(action_id), selector={'host': host.id})


class HostConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.HostConfigSerializer

    def get(self, request, host_id):   # pylint: disable=arguments-differ
        """
        Show current config for a specified host
        """
        check_obj(Host, host_id, 'HOST_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(obj, context={'request': request, 'host_id': host_id})
        return Response(serializer.data)


class HostConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.HostConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, host_id):
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        return (host, self.get_queryset().get(obj_ref=cc, id=cc.current))

    def get(self, request, host_id):   # pylint: disable=arguments-differ
        """
        Show history of config of a specified host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        obj = self.get_queryset().filter(obj_ref=cc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, host_id):
        """
        Update config of a specified host. Config parameter is json
        """
        obj, cl = self.get_obj(host_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class HostConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, host_id, version):   # pylint: disable=arguments-differ
        """
        Show config for a specified version and host.

        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(host, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class HostConfigRestore(GenericAPIView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfigRestore

    def patch(self, request, host_id, version):
        """
        Restore config of specified version of a specified host.
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        try:
            obj = self.get_queryset().get(obj_ref=cc, id=version)
        except ConfigLog.DoesNotExist:
            raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)
