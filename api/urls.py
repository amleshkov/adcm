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

from django.urls import path, register_converter
from django.conf.urls import include

from rest_framework_swagger.views import get_swagger_view
from rest_framework.schemas import get_schema_view

from api import views, stack_views, cluster_views, docs


register_converter(views.NameConverter, 'name')
swagger_view = get_swagger_view(title='ArenaData Chapel API')
schema_view = get_schema_view(title='ArenaData Chapel API')


CLUSTER = 'cluster/<int:cluster_id>/'
PROVIDER = 'provider/<int:provider_id>/'
HOST = 'host/<int:host_id>/'
SERVICE = 'service/<int:service_id>/'
ADCM_CONFIG = 'adcm/<int:adcm_id>/config/'
CLUSTER_CONFIG = CLUSTER + 'config/'
PROVIDER_CONFIG = PROVIDER + 'config/'
HOST_CONFIG = HOST + 'config/'
SERVICE_CONFIG = CLUSTER + SERVICE + 'config/'


urlpatterns = [
    path('info/', views.ADCMInfo.as_view(), name='adcm-info'),
    path('token/', views.GetAuthToken.as_view(), name='token'),

    path('user/', views.UserList.as_view(), name='user-list'),
    path('user/<name:username>/', views.UserDetail.as_view(), name='user-details'),
    path('user/<name:username>/password/', views.UserPasswd.as_view(), name='user-passwd'),

    path('profile/', views.ProfileList.as_view(), name='profile-list'),
    path('profile/<name:username>/', views.ProfileDetail.as_view(), name='profile-details'),
    path(
        'profile/<name:username>/password/', views.UserPasswd.as_view(), name='profile-passwd'
    ),

    path('stats/', views.Stats.as_view(), name='stats'),
    path('stats/task/<int:task_id>/', views.TaskStats.as_view(), name='task-stats'),
    path('stats/job/<int:job_id>/', views.JobStats.as_view(), name='job-stats'),

    path('stack/', stack_views.Stack.as_view(), name='stack'),
    path('stack/upload/', stack_views.UploadBundle.as_view(), name='upload-bundle'),
    path('stack/load/', stack_views.LoadBundle.as_view(), name='load-bundle'),
    path(
        'stack/load/servicemap/',
        stack_views.LoadServiceMap.as_view(),
        name='load-servicemap'
    ),
    path('stack/bundle/', stack_views.BundleList.as_view(), name='bundle'),
    path(
        'stack/bundle/<int:bundle_id>/',
        stack_views.BundleDetail.as_view(),
        name='bundle-details'
    ),
    path(
        'stack/bundle/<int:bundle_id>/update/',
        stack_views.BundleUpdate.as_view(),
        name='bundle-update'
    ),
    path(
        'stack/bundle/<int:bundle_id>/license/',
        stack_views.BundleLicense.as_view(),
        name='bundle-license'
    ),
    path(
        'stack/bundle/<int:bundle_id>/license/accept/',
        stack_views.AcceptLicense.as_view(),
        name='accept-license'
    ),
    path(
        'stack/action/<int:action_id>/',
        stack_views.ProtoActionDetail.as_view(),
        name='action-details'
    ),
    path('stack/prototype/', stack_views.PrototypeList.as_view(), name='prototype'),
    path('stack/service/', stack_views.ServiceList.as_view(), name='service-type'),
    path(
        'stack/service/<int:prototype_id>/',
        stack_views.ServiceDetail.as_view(),
        name='service-type-details'
    ),
    path(
        'stack/' + SERVICE + 'action/',
        stack_views.ServiceProtoActionList.as_view(),
        name='service-actions'
    ),
    path('stack/provider/', stack_views.ProviderTypeList.as_view(), name='provider-type'),
    path(
        'stack/provider/<int:prototype_id>/',
        stack_views.ProviderTypeDetail.as_view(),
        name='provider-type-details'
    ),
    path('stack/host/', stack_views.HostTypeList.as_view(), name='host-type'),
    path(
        'stack/host/<int:prototype_id>/',
        stack_views.HostTypeDetail.as_view(),
        name='host-type-details'
    ),
    path('stack/cluster/', stack_views.ClusterTypeList.as_view(), name='cluster-type'),
    path(
        'stack/cluster/<int:prototype_id>/',
        stack_views.ClusterTypeDetail.as_view(),
        name='cluster-type-details'
    ),
    path('stack/adcm/', stack_views.AdcmTypeList.as_view(), name='adcm-type'),
    path(
        'stack/adcm/<int:prototype_id>/',
        stack_views.AdcmTypeDetail.as_view(),
        name='adcm-type-details'
    ),
    path(
        'stack/prototype/<int:prototype_id>/',
        stack_views.PrototypeDetail.as_view(),
        name='prototype-details'
    ),

    path('cluster/', cluster_views.ClusterList.as_view(), name='cluster'),
    path(CLUSTER, cluster_views.ClusterDetail.as_view(), name='cluster-details'),
    path(CLUSTER + 'action/', cluster_views.ClusterActionList.as_view(), name='cluster-action'),
    path(CLUSTER + 'host/', cluster_views.ClusterHostList.as_view(), name='cluster-host'),
    path(CLUSTER + 'import/', cluster_views.ClusterImport.as_view(), name='cluster-import'),
    path(CLUSTER + 'upgrade/', cluster_views.ClusterUpgrade.as_view(), name='cluster-upgrade'),
    path(CLUSTER + 'bind/', cluster_views.ClusterBindList.as_view(), name='cluster-bind'),
    path(
        CLUSTER + 'bind/<int:bind_id>/',
        cluster_views.ClusterServiceBindDetail.as_view(),
        name='cluster-bind-details'
    ),
    path(
        CLUSTER + 'serviceprototype/',
        cluster_views.ClusterBundle.as_view(),
        name='cluster-service-prototype'
    ),
    path(
        CLUSTER + 'upgrade/<int:upgrade_id>/',
        cluster_views.ClusterUpgradeDetail.as_view(),
        name='cluster-upgrade-details'
    ),
    path(
        CLUSTER + 'upgrade/<int:upgrade_id>/do/',
        cluster_views.DoClusterUpgrade.as_view(),
        name='do-cluster-upgrade'
    ),
    path(
        CLUSTER + HOST, cluster_views.ClusterHostDetail.as_view(), name='cluster-host-details'
    ),
    path(
        CLUSTER + 'service/', cluster_views.ClusterServiceList.as_view(), name='cluster-service'
    ),
    path(
        CLUSTER + HOST + 'action/',
        cluster_views.ClusterHostActionList.as_view(),
        name='cluster-host-action'
    ),
    path(
        CLUSTER + HOST + 'action/<int:action_id>/',
        cluster_views.ClusterHostAction.as_view(),
        name='cluster-host-action-details'
    ),
    path(
        CLUSTER + HOST + 'action/<int:action_id>/run/',
        cluster_views.ClusterHostTask.as_view(),
        name='cluster-host-action-run'
    ),
    path(
        CLUSTER + 'action/<int:action_id>/',
        cluster_views.ClusterAction.as_view(),
        name='cluster-action-details'
    ),
    path(
        CLUSTER + 'action/<int:action_id>/run/',
        cluster_views.ClusterTask.as_view(),
        name='cluster-action-run'
    ),
    path(
        CLUSTER + 'status/',
        cluster_views.StatusList.as_view(),
        name='cluster-status'
    ),
    path(
        CLUSTER + 'hostcomponent/',
        cluster_views.HostComponentList.as_view(),
        name='host-component'
    ),
    path(
        CLUSTER + 'hostcomponent/<int:hs_id>/',
        cluster_views.HostComponentDetail.as_view(),
        name='host-component-details'
    ),
    path(
        CLUSTER + SERVICE,
        cluster_views.ClusterServiceDetail.as_view(),
        name='cluster-service-details'
    ),
    path(
        CLUSTER + SERVICE + 'action/',
        cluster_views.ClusterServiceActionList.as_view(),
        name='cluster-service-action'
    ),
    path(
        CLUSTER + SERVICE + 'action/<int:action_id>/',
        cluster_views.ClusterServiceAction.as_view(),
        name='cluster-service-action-details'
    ),
    path(
        CLUSTER + SERVICE + 'action/<int:action_id>/run/',
        cluster_views.ClusterServiceTask.as_view(),
        name='cluster-service-action-run'
    ),
    path(
        CLUSTER + SERVICE + 'component/',
        cluster_views.ServiceComponentList.as_view(),
        name='service-component'
    ),
    path(
        CLUSTER + SERVICE + 'component/<int:component_id>/',
        cluster_views.ServiceComponentDetail.as_view(),
        name='service-component-details'
    ),
    path(
        CLUSTER + SERVICE + 'import/',
        cluster_views.ClusterServiceImport.as_view(),
        name='cluster-service-import'
    ),
    path(
        CLUSTER + SERVICE + 'bind/',
        cluster_views.ClusterServiceBind.as_view(),
        name='cluster-service-bind'
    ),
    path(
        CLUSTER + SERVICE + 'bind/<int:bind_id>/',
        cluster_views.ClusterServiceBindDetail.as_view(),
        name='cluster-service-bind-details'
    ),
    path(
        CLUSTER_CONFIG,
        cluster_views.ClusterConfig.as_view(),
        {'service_id': 0},
        name='cluster-config'
    ),
    path(
        CLUSTER_CONFIG + 'history/',
        cluster_views.ClusterConfigHistory.as_view(),
        {'service_id': 0},
        name='cluster-config-history'
    ),
    path(
        CLUSTER_CONFIG + 'history/<int:version>/',
        cluster_views.ClusterConfigVersion.as_view(),
        {'service_id': 0},
        name='cluster-config-id'
    ),
    path(
        CLUSTER_CONFIG + 'previous/',
        cluster_views.ClusterConfigVersion.as_view(),
        {'service_id': 0, 'version': 'previous'},
        name='cluster-config-prev'
    ),
    path(
        CLUSTER_CONFIG + 'current/',
        cluster_views.ClusterConfigVersion.as_view(),
        {'service_id': 0, 'version': 'current'},
        name='cluster-config-curr'
    ),
    path(
        CLUSTER_CONFIG + 'history/<int:version>/restore/',
        cluster_views.ClusterConfigRestore.as_view(),
        {'service_id': 0},
        name='cluster-config-restore'
    ),
    path(
        SERVICE_CONFIG,
        cluster_views.ClusterServiceConfig.as_view(),
        name='cluster-service-config'
    ),
    path(
        SERVICE_CONFIG + 'previous/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        {'version': 'previous'},
        name='cluster-service-config-prev'
    ),
    path(
        SERVICE_CONFIG + 'current/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        {'version': 'current'},
        name='cluster-service-config-curr'
    ),
    path(
        SERVICE_CONFIG + 'history/<int:version>/',
        cluster_views.ClusterServiceConfigVersion.as_view(),
        name='cluster-service-config-id'
    ),
    path(
        SERVICE_CONFIG + 'history/<int:version>/restore/',
        cluster_views.ClusterConfigRestore.as_view(),
        name='cluster-service-config-restore'
    ),
    path(
        SERVICE_CONFIG + 'history/',
        cluster_views.ClusterServiceConfigHistory.as_view(),
        name='cluster-service-config-history'
    ),

    path('adcm/', views.AdcmList.as_view(), name='adcm'),
    path('adcm/<int:adcm_id>/', views.AdcmDetail.as_view(), name='adcm-details'),
    path(ADCM_CONFIG, views.AdcmConfig.as_view(), name='adcm-config'),
    path(
        ADCM_CONFIG + 'history/',
        views.AdcmConfigHistory.as_view(),
        name='adcm-config-history'
    ),
    path(
        ADCM_CONFIG + 'history/<int:version>/',
        views.AdcmConfigVersion.as_view(),
        name='adcm-config-id'
    ),
    path(
        ADCM_CONFIG + 'previous/',
        views.AdcmConfigVersion.as_view(),
        {'version': 'previous'},
        name='adcm-config-prev'
    ),
    path(
        ADCM_CONFIG + 'current/',
        views.AdcmConfigVersion.as_view(),
        {'version': 'current'},
        name='adcm-config-curr'
    ),
    path('adcm/<int:adcm_id>/action/', views.ADCMActionList.as_view(), name='adcm-action'),
    path(
        'adcm/<int:adcm_id>/action/<int:action_id>/',
        views.ADCMAction.as_view(),
        name='adcm-action-details'
    ),
    path(
        'adcm/<int:adcm_id>/action/<int:action_id>/run/',
        views.ADCMTask.as_view(),
        name='adcm-action-run'
    ),
    path('provider/', views.ProviderList.as_view(), name='provider'),
    path(PROVIDER, views.ProviderDetail.as_view(), name='provider-details'),
    path(PROVIDER + 'host/', views.ProviderHostList.as_view(), name='provider-host'),

    path(PROVIDER + 'action/', views.ProviderActionList.as_view(), name='provider-action'),
    path(
        PROVIDER + 'action/<int:action_id>/',
        views.ProviderAction.as_view(),
        name='provider-action-details'
    ),
    path(
        PROVIDER + 'action/<int:action_id>/run/',
        views.ProviderTask.as_view(),
        name='provider-action-run'
    ),
    path(PROVIDER + 'upgrade/', views.ProviderUpgrade.as_view(), name='provider-upgrade'),
    path(
        PROVIDER + 'upgrade/<int:upgrade_id>/',
        views.ProviderUpgradeDetail.as_view(),
        name='provider-upgrade-details'
    ),
    path(
        PROVIDER + 'upgrade/<int:upgrade_id>/do/',
        views.DoProviderUpgrade.as_view(),
        name='do-provider-upgrade'
    ),

    path(PROVIDER_CONFIG, views.ProviderConfig.as_view(), name='provider-config'),
    path(
        PROVIDER_CONFIG + 'history/',
        views.ProviderConfigHistory.as_view(),
        name='provider-config-history'
    ),
    path(
        PROVIDER_CONFIG + 'history/<int:version>/',
        views.ProviderConfigVersion.as_view(),
        name='provider-config-id'
    ),
    path(
        PROVIDER_CONFIG + 'previous/',
        views.ProviderConfigVersion.as_view(),
        {'version': 'previous'},
        name='provider-config-prev'
    ),
    path(
        PROVIDER_CONFIG + 'current/',
        views.ProviderConfigVersion.as_view(),
        {'version': 'current'},
        name='provider-config-curr'
    ),
    path(
        PROVIDER_CONFIG + 'history/<int:version>/restore/',
        views.ProviderConfigRestore.as_view(),
        name='provider-config-restore'
    ),

    path('host/', views.HostList.as_view(), name='host'),
    path(HOST, views.HostDetail.as_view(), name='host-details'),

    path(HOST + 'action/', views.HostActionList.as_view(), name='host-action'),
    path(
        HOST + 'action/<int:action_id>/',
        views.HostAction.as_view(),
        name='host-action-details'
    ),
    path(
        HOST + 'action/<int:action_id>/run/',
        views.HostTask.as_view(),
        name='host-action-run'
    ),
    path(HOST_CONFIG, views.HostConfig.as_view(), name='host-config'),
    path(
        HOST_CONFIG + 'history/', views.HostConfigHistory.as_view(), name='host-config-history'
    ),
    path(
        HOST_CONFIG + 'history/<int:version>/',
        views.HostConfigVersion.as_view(),
        name='host-config-id'
    ),
    path(
        HOST_CONFIG + 'previous/',
        views.HostConfigVersion.as_view(),
        {'version': 'previous'},
        name='host-config-prev'
    ),
    path(
        HOST_CONFIG + 'current/',
        views.HostConfigVersion.as_view(),
        {'version': 'current'},
        name='host-config-curr'
    ),
    path(
        HOST_CONFIG + 'history/<int:version>/restore/',
        views.HostConfigRestore.as_view(),
        name='host-config-restore'
    ),

    path('task/', views.Task.as_view(), name='task'),
    path('task/<int:task_id>/', views.TaskDetail.as_view(), name='task-details'),
    path('task/<int:task_id>/restart/', views.TaskReStart.as_view(), name='task-restart'),

    path('job/', views.JobList.as_view(), name='job'),
    path('job/<int:job_id>/', views.JobDetail.as_view(), name='job-details'),
    path(
        'job/<int:job_id>/log/<name:tag>/<name:level>/<name:log_type>/',
        views.LogFile.as_view(),
        name='log-file'
    ),
    # path('docs/', include_docs_urls(title='ArenaData Chapel API')),
    path('swagger/', swagger_view),
    path('schema/', schema_view),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    path('docs/md/', docs.docs_md),
    path('docs/', docs.docs_html),

    path('', views.APIRoot.as_view()),
]
