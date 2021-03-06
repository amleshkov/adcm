# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain a
# copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from django.db import IntegrityError, transaction

import cm.errors
import cm.issue
import cm.config as config
import cm.status_api
from cm.logger import log   # pylint: disable=unused-import
from cm.upgrade import check_license, version_in
from cm.adcm_config import proto_ref, obj_ref, prepare_social_auth
from cm.adcm_config import process_file_type, read_bundle_file, get_prototype_config
from cm.adcm_config import init_object_config, save_obj_config, check_json_config
from cm.errors import AdcmApiEx
from cm.errors import raise_AdcmEx as err
from cm.models import Cluster, Prototype, Component, Host, HostComponent, ADCM
from cm.models import ClusterObject, ServiceComponent, ConfigLog, HostProvider
from cm.models import PrototypeImport, PrototypeExport, ClusterBind


def check_proto_type(proto, check_type):
    if proto.type != check_type:
        msg = 'Prototype type should be {}, not {}'
        err('OBJ_TYPE_ERROR', msg.format(check_type, proto.type))


def add_cluster(proto, name, desc=''):
    check_proto_type(proto, 'cluster')
    check_license(proto.bundle)
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        cluster = Cluster(prototype=proto, name=name, config=obj_conf, description=desc)
        cluster.save()
        process_file_type(cluster, spec, conf)
        cm.issue.save_issue(cluster)
    cm.status_api.post_event('create', 'cluster', cluster.id)
    cm.status_api.load_service_map()
    return cluster


def add_host(proto, provider, fqdn, desc=''):
    check_proto_type(proto, 'host')
    check_license(proto.bundle)
    if proto.bundle != provider.prototype.bundle:
        msg = 'Host prototype bundle #{} does not match with host provider bundle #{}'
        err('FOREIGN_HOST', msg.format(proto.bundle.id, provider.prototype.bundle.id))
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        host = Host(
            prototype=proto,
            provider=provider,
            fqdn=fqdn,
            config=obj_conf,
            description=desc
        )
        host.save()
        process_file_type(host, spec, conf)
        cm.issue.save_issue(host)
    cm.status_api.post_event('create', 'host', host.id, 'provider', str(provider.id))
    cm.status_api.load_service_map()
    return host


def add_provider_host(provider_id, fqdn, desc=''):
    try:
        provider = HostProvider.objects.get(id=provider_id)
    except HostProvider.DoesNotExist:
        err('PROVIDER_NOT_FOUND', 'Host Provider with id #{} is not found'.format(provider_id))
    try:
        Host.objects.get(fqdn=fqdn)
        err('HOST_CONFLICT', 'Host with fqdn "{}" already exists'.format(fqdn))
    except Host.DoesNotExist:
        pass
    proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
    return add_host(proto, provider, fqdn, desc)


def add_host_provider(proto, name, desc=''):
    check_proto_type(proto, 'provider')
    check_license(proto.bundle)
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        provider = HostProvider(prototype=proto, name=name, config=obj_conf, description=desc)
        provider.save()
        process_file_type(provider, spec, conf)
        cm.issue.save_issue(provider)
    cm.status_api.post_event('create', 'provider', provider.id)
    return provider


def delete_host_provider(provider):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        msg = 'There is host #{} "{}" of host {}'
        err('PROVIDER_CONFLICT', msg.format(hosts[0].id, hosts[0].fqdn, obj_ref(provider)))
    cm.status_api.post_event('delete', 'provider', provider.id)
    provider.delete()


def add_host_to_cluster(cluster, host):
    if host.cluster:
        if host.cluster.id != cluster.id:
            msg = 'Host #{} belong to cluster {}'.format(host.id, host.cluster.id)
            err('FOREIGN_HOST', msg)
        else:
            err('HOST_CONFLICT')
    with transaction.atomic():
        host.cluster = cluster
        host.save()
        cm.issue.save_issue(host)
        cm.issue.save_issue(cluster)
    cm.status_api.post_event('add', 'host', host.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    return host


def delete_host(host):
    cluster = host.cluster
    if cluster:
        msg = 'Host #{} "{}" belong to {}'
        err('HOST_CONFLICT', msg.format(host.id, host.fqdn, obj_ref(cluster)))
    cm.status_api.post_event('delete', 'host', host.id)
    host.delete()
    cm.status_api.load_service_map()


def delete_service(service):
    if HostComponent.objects.filter(cluster=service.cluster, service=service):
        err('SERVICE_CONFLICT', 'Service #{} has component(s) on host(s)'.format(service.id))
    if ClusterBind.objects.filter(source_service=service):
        err('SERVICE_CONFLICT', 'Service #{} has exports(s)'.format(service.id))
    cm.status_api.post_event('delete', 'service', service.id)
    service.delete()
    cm.status_api.load_service_map()


def delete_cluster(cluster):
    cm.status_api.post_event('delete', 'cluster', cluster.id)
    cluster.delete()
    cm.status_api.load_service_map()


def remove_host_from_cluster(host):
    cluster = host.cluster
    hc = HostComponent.objects.filter(cluster=cluster, host=host)
    if hc:
        return err('HOST_CONFLICT', 'Host #{} has component(s)'.format(host.id))
    with transaction.atomic():
        host.cluster = None
        host.save()
        cm.issue.save_issue(cluster)
    cm.status_api.post_event('remove', 'host', host.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    return host


def unbind(cbind):
    import_obj = get_bind_obj(cbind.cluster, cbind.service)
    export_obj = get_bind_obj(cbind.source_cluster, cbind.source_service)
    check_import_default(import_obj, export_obj)
    cm.status_api.post_event('delete', 'bind', cbind.id, 'cluster', str(cbind.cluster.id))
    with transaction.atomic():
        cbind.delete()
        cm.issue.save_issue(cbind.cluster)


def add_service_to_cluster(cluster, proto):
    check_proto_type(proto, 'service')
    check_license(proto.bundle)
    if not proto.shared:
        if cluster.prototype.bundle != proto.bundle:
            msg = '{} does not belong to bundle "{}" {}'
            err('SERVICE_CONFLICT', msg.format(
                proto_ref(proto), cluster.prototype.bundle.name, cluster.prototype.version
            ))
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        cs = ClusterObject(cluster=cluster, prototype=proto, config=obj_conf)
        cs.save()
        add_components_to_service(cluster, cs)
        process_file_type(cs, spec, conf)
        cm.issue.save_issue(cs)
        cm.issue.save_issue(cluster)
    cm.status_api.post_event('add', 'service', cs.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    return cs


def add_components_to_service(cluster, service):
    for comp in Component.objects.filter(prototype=service.prototype):
        sc = ServiceComponent(cluster=cluster, service=service, component=comp)
        sc.save()


def get_bundle_proto(bundle):
    proto = Prototype.objects.filter(bundle=bundle, name=bundle.name)
    return proto[0]


def get_license(bundle):
    if not bundle.license_path:
        return None
    ref = 'bundle "{}" {}'.format(bundle.name, bundle.version)
    proto = get_bundle_proto(bundle)
    return read_bundle_file(proto, bundle.license_path, bundle.hash, 'license file', ref)


def accept_license(bundle):
    if not bundle.license_path:
        err('LICENSE_ERROR', 'This bundle has no license')
    if bundle.license == 'absent':
        err('LICENSE_ERROR', 'This bundle has no license')
    bundle.license = 'accepted'
    bundle.save()


def update_obj_config(obj_conf, conf, attr=None, desc=''):
    if hasattr(obj_conf, 'adcm'):
        obj = obj_conf.adcm
        proto = obj_conf.adcm.prototype
    elif hasattr(obj_conf, 'clusterobject'):
        obj = obj_conf.clusterobject
        proto = obj_conf.clusterobject.prototype
    elif hasattr(obj_conf, 'cluster'):
        obj = obj_conf.cluster
        proto = obj_conf.cluster.prototype
    elif hasattr(obj_conf, 'host'):
        obj = obj_conf.host
        proto = obj_conf.host.prototype
    elif hasattr(obj_conf, 'hostprovider'):
        obj = obj_conf.hostprovider
        proto = obj_conf.hostprovider.prototype
    else:
        err('INVALID_CONFIG_UPDATE', 'unknown object type "{}"'.format(obj_conf))
    old_conf = ConfigLog.objects.get(obj_ref=obj_conf, id=obj_conf.current)
    if not attr:
        if old_conf.attr:
            attr = json.loads(old_conf.attr)
    new_conf = check_json_config(proto, obj, conf, old_conf.config, attr)
    with transaction.atomic():
        cl = save_obj_config(obj_conf, new_conf, desc, attr)
        cm.issue.save_issue(obj)
    if hasattr(obj_conf, 'adcm'):
        prepare_social_auth(new_conf)
    cm.status_api.post_event('change_config', proto.type, obj.id, 'version', str(cl.id))
    return cl


def has_google_oauth():
    adcm = ADCM.objects.filter()
    if not adcm:
        return False
    cl = ConfigLog.objects.get(obj_ref=adcm[0].config, id=adcm[0].config.current)
    conf = json.loads(cl.config)
    if 'google_oauth' not in conf:
        return False
    gconf = conf['google_oauth']
    if 'client_id' not in gconf or not gconf['client_id']:
        return False
    return True


def check_hc(cluster, hc_in):   # pylint: disable=too-many-branches
    def check_sub(sub_key, sub_type, item):
        if sub_key not in item:
            msg = '"{}" sub-field of hostcomponent is required'
            raise AdcmApiEx('INVALID_INPUT', msg.format(sub_key))
        if not isinstance(item[sub_key], sub_type):
            msg = '"{}" sub-field of hostcomponent should be "{}"'
            raise AdcmApiEx('INVALID_INPUT', msg.format(sub_key, sub_type))

    seen = {}
    if not isinstance(hc_in, list):
        raise AdcmApiEx('INVALID_INPUT', 'hostcomponent should be array')
    for item in hc_in:
        for sub_key, sub_type in (('service_id', int), ('host_id', int), ('component_id', int)):
            check_sub(sub_key, sub_type, item)
        key = (item.get('service_id', ''), item.get('host_id', ''), item.get('component_id', ''))
        if key not in seen:
            seen[key] = 1
        else:
            msg = 'duplicate ({}) in host service list'
            raise AdcmApiEx('INVALID_INPUT', msg.format(item))

    host_comp_list = []
    for item in hc_in:
        try:
            host = Host.objects.get(id=item['host_id'])
        except Host.DoesNotExist:
            msg = 'No host #{}'.format(item['host_id'])
            raise AdcmApiEx('HOST_NOT_FOUND', msg)
        try:
            service = ClusterObject.objects.get(id=item['service_id'], cluster=cluster)
        except ClusterObject.DoesNotExist:
            msg = 'No service #{} in {}'.format(item['service_id'], obj_ref(cluster))
            raise AdcmApiEx('SERVICE_NOT_FOUND', msg)
        try:
            comp = ServiceComponent.objects.get(
                id=item['component_id'], cluster=cluster, service=service
            )
        except ServiceComponent.DoesNotExist:
            msg = 'No component #{} in {} '.format(item['component_id'], obj_ref(service))
            raise AdcmApiEx('COMPONENT_NOT_FOUND', msg)
        if not host.cluster:
            msg = 'host #{} {} does not belong to any cluster'.format(host.id, host.fqdn)
            raise AdcmApiEx("FOREIGN_HOST", msg)
        if host.cluster.id != cluster.id:
            msg = 'host {} (cluster #{}) does not belong to cluster #{}'
            raise AdcmApiEx("FOREIGN_HOST", msg.format(host.fqdn, host.cluster.id, cluster.id))
        host_comp_list.append((service, host, comp))

    for service in ClusterObject.objects.filter(cluster=cluster):
        cm.issue.check_component_constraint(service, [i for i in host_comp_list if i[0] == service])

    return host_comp_list


def save_hc(cluster, host_comp_list):
    HostComponent.objects.filter(cluster=cluster).delete()
    result = []
    for (proto, host, comp) in host_comp_list:
        hc = HostComponent(
            cluster=cluster,
            service=proto,
            host=host,
            component=comp,
        )
        hc.save()
        result.append(hc)
    cm.status_api.post_event('change_hostcomponentmap', 'cluster', cluster.id)
    cm.issue.save_issue(cluster)
    cm.status_api.load_service_map()
    return result


def add_hc(cluster, hc_in):
    host_comp_list = check_hc(cluster, hc_in)
    with transaction.atomic():
        new_hc = save_hc(cluster, host_comp_list)
    return new_hc


def get_bind(cluster, service, source_cluster, source_service):
    try:
        return ClusterBind.objects.get(
            cluster=cluster,
            service=service,
            source_cluster=source_cluster,
            source_service=source_service
        )
    except ClusterBind.DoesNotExist:
        return None


def get_import(cluster, service=None):
    def get_export(cluster, service, pi):
        exports = []
        export_proto = {}
        for pe in PrototypeExport.objects.filter(prototype__name=pi.name):
            # Merge all export groups of prototype to one export
            if pe.prototype.id in export_proto:
                continue
            export_proto[pe.prototype.id] = True
            if not version_in(pe.prototype.version, pi.min_version, pi.max_version):
                continue
            if pe.prototype.type == 'cluster':
                for cls in Cluster.objects.filter(prototype=pe.prototype):
                    binded = get_bind(cluster, service, cls, None)
                    exports.append({
                        'obj_name': cls.name,
                        'bundle_name': cls.prototype.display_name,
                        'bundle_version': cls.prototype.version,
                        'id': {'cluster_id': cls.id},
                        'binded': bool(binded),
                        'bind_id': getattr(binded, 'id', None),
                    })
            elif pe.prototype.type == 'service':
                for co in ClusterObject.objects.filter(prototype=pe.prototype):
                    binded = get_bind(cluster, service, co.cluster, co)
                    exports.append({
                        'obj_name': co.cluster.name + '/' + co.prototype.display_name,
                        'bundle_name': co.prototype.display_name,
                        'bundle_version': co.prototype.version,
                        'id': {'cluster_id': co.cluster.id, 'service_id': co.id},
                        'binded': bool(binded),
                        'bind_id': getattr(binded, 'id', None),
                    })
            else:
                err('BIND_ERROR', 'unexpected export type: {}'.format(pe.prototype.type))
        return exports

    imports = []
    proto = cluster.prototype
    if service:
        proto = service.prototype
    for pi in PrototypeImport.objects.filter(prototype=proto):
        imports.append({
            'id': pi.id,
            'name': pi.name,
            'required': pi.required,
            'multibind': pi.multibind,
            'exports': get_export(cluster, service, pi)
        })
    return imports


def check_bind_post(bind_list):
    if not isinstance(bind_list, list):
        err('BIND_ERROR', 'bind should be an array')
    for b in bind_list:
        if not isinstance(b, dict):
            err('BIND_ERROR', 'bind item should be a map')
        if 'import_id' not in b:
            err('BIND_ERROR', 'bind item does not have required "import_id" key')
        if not isinstance(b['import_id'], int):
            err('BIND_ERROR', 'bind item "import_id" value should be integer')
        if 'export_id' not in b:
            err('BIND_ERROR', 'bind item does not have required "export_id" key')
        if not isinstance(b['export_id'], dict):
            err('BIND_ERROR', 'bind item "export_id" value should be a map')
        if 'cluster_id' not in b['export_id']:
            err('BIND_ERROR', 'bind item export_id does not have required "cluster_id" key')
        if not isinstance(b['export_id']['cluster_id'], int):
            err('BIND_ERROR', 'bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj, export_obj):
    pi = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not pi.default:
        return
    cl = ConfigLog.objects.get(obj_ref=import_obj.config, id=import_obj.config.current)
    if not cl.attr:
        return
    attr = json.loads(cl.attr)
    for name in json.loads(pi.default):
        if name in attr:
            if 'active' in attr[name] and not attr[name]['active']:
                msg = 'Default import "{}" for {} is inactive'
                err('BIND_ERROR', msg.format(name, obj_ref(import_obj)))


def get_bind_obj(cluster, service):
    obj = cluster
    if service:
        obj = service
    return obj


def multi_bind(cluster, service, bind_list):   # pylint: disable=too-many-locals,too-many-statements
    def get_pi(import_id, import_obj):
        try:
            pi = PrototypeImport.objects.get(id=import_id)
        except PrototypeImport.DoesNotExist:
            err('BIND_ERROR', 'Import with id #{} does not found'.format(import_id))
        if pi.prototype != import_obj.prototype:
            msg = 'Import #{} does not belong to {}'
            err('BIND_ERROR', msg.format(import_id, obj_ref(import_obj)))
        return pi

    def get_export_service(b, export_cluster):
        export_co = None
        if 'service_id' in b['export_id']:
            try:
                export_co = ClusterObject.objects.get(id=b['export_id']['service_id'])
            except ClusterObject.DoesNotExist:
                msg = 'export service with id #{} not found'
                err('BIND_ERROR', msg.format(b['export_id']['service_id']))
            if export_co.cluster != export_cluster:
                msg = 'export {} is not belong to {}'
                err('BIND_ERROR', msg.format(obj_ref(export_co), obj_ref(export_cluster)))
        return export_co

    def cook_key(cluster, service):
        if service:
            return f'{cluster.id}.{service.id}'
        return str(cluster.id)

    check_bind_post(bind_list)
    import_obj = get_bind_obj(cluster, service)
    old_bind = {}
    cb_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cb in cb_list:
        old_bind[cook_key(cb.source_cluster, cb.source_service)] = cb

    new_bind = {}
    for b in bind_list:
        pi = get_pi(b['import_id'], import_obj)
        try:
            export_cluster = Cluster.objects.get(id=b['export_id']['cluster_id'])
        except Cluster.DoesNotExist:
            msg = 'export cluster with id #{} not found'
            err('BIND_ERROR', msg.format(b['export_id']['cluster_id']))
        export_obj = export_cluster
        export_co = get_export_service(b, export_cluster)
        if export_co:
            export_obj = export_co

        if cook_key(export_cluster, export_co) in new_bind:
            err('BIND_ERROR', 'Bind list has duplicates')

        if pi.name != export_obj.prototype.name:
            msg = 'Export {} does not match import name "{}"'
            err('BIND_ERROR', msg.format(obj_ref(export_obj), pi.name))
        if not version_in(export_obj.prototype.version, pi.min_version, pi.max_version):
            msg = 'Import "{}" of {} versions ({}, {}) does not match export version: {} ({})'
            err('BIND_ERROR', msg.format(
                export_obj.prototype.name, proto_ref(pi.prototype), pi.min_version, pi.max_version,
                export_obj.prototype.version, obj_ref(export_obj)
            ))
        cbind = ClusterBind(
            cluster=cluster,
            service=service,
            source_cluster=export_cluster,
            source_service=export_co
        )
        new_bind[cook_key(export_cluster, export_co)] = (pi, cbind, export_obj)

    with transaction.atomic():
        for key in new_bind:
            if key in old_bind:
                continue
            (pi, cb, export_obj) = new_bind[key]
            check_multi_bind(pi, cluster, service, cb.source_cluster, cb.source_service, cb_list)
            cb.save()
            log.info('bind %s to %s', obj_ref(export_obj), obj_ref(import_obj))

        for key in old_bind:
            if key in new_bind:
                continue
            export_obj = get_bind_obj(old_bind[key].source_cluster, old_bind[key].source_service)
            check_import_default(import_obj, export_obj)
            old_bind[key].delete()
            log.info('unbind %s from %s', obj_ref(export_obj), obj_ref(import_obj))

        cm.issue.save_issue(cluster)

    return get_import(cluster, service)


def bind(cluster, export_cluster, export_service_id):   # pylint: disable=too-many-branches
    if cluster.id == export_cluster.id:
        err('BIND_ERROR', 'can not bind cluster to themself')
    imports = PrototypeImport.objects.filter(prototype=cluster.prototype)
    if not imports:
        err('BIND_ERROR', '{} do not have imports'.format(proto_ref(cluster.prototype)))

    if export_service_id:
        try:
            export_service = ClusterObject.objects.get(cluster=export_cluster, id=export_service_id)
            if not PrototypeExport.objects.filter(prototype=export_service.prototype):
                err('BIND_ERROR', '{} do not have exports'.format(obj_ref(export_service)))
        except ClusterObject.DoesNotExist:
            msg = 'service #{} does not exists or does not belong to cluster # {}'
            err('SERVICE_NOT_FOUND', msg.format(export_service_id, export_cluster.id))
    else:
        if not PrototypeExport.objects.filter(prototype=export_cluster.prototype):
            err('BIND_ERROR', '{} do not have exports'.format(obj_ref(cluster)))
        if bool(get_bind(cluster, None, export_cluster, None)):
            err('BIND_ERROR', 'cluster already binded')
        export_service = None

    actual_import = None
    for imp in imports:
        if export_service:
            if export_service.prototype.name == imp.name:
                actual_import = imp
        else:
            if export_cluster.prototype.name == imp.name:
                actual_import = imp

    if not actual_import:
        msg = 'Export {} does not match import names'
        if export_service:
            proto = export_service.prototype
        else:
            proto = export_cluster.prototype
        err('BIND_ERROR', msg.format(proto_ref(proto)))

    check_multi_bind(actual_import, cluster, None, export_cluster, export_service)
    # To do: check versions

    try:
        if bool(get_bind(cluster, None, export_cluster, export_service)):
            err('BIND_ERROR', 'cluster already binded')
        with transaction.atomic():
            cbind = ClusterBind(
                cluster=cluster, source_cluster=export_cluster, source_service=export_service
            )
            cbind.save()
            cm.issue.save_issue(cbind.cluster)
    except IntegrityError:
        err('BIND_ERROR', 'cluster already binded')
    return {
        'id': cbind.id,
        'export_cluster_id': export_cluster.id,
        'export_cluster_name': export_cluster.name,
        'export_cluster_prototype_name': export_cluster.prototype.name,
    }


def check_multi_bind(actual_import, cluster, service, export_cluster, export_service, cb_list=None):
    if actual_import.multibind:
        return
    if not cb_list:
        cb_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cb in cb_list:
        if cb.source_service:
            source_proto = cb.source_service.prototype
        else:
            source_proto = cb.source_cluster.prototype
        if export_service:
            if source_proto == export_service.prototype:
                msg = 'can not multi bind {} to {}'
                err('BIND_ERROR', msg.format(proto_ref(source_proto), obj_ref(cluster)))
        else:
            if source_proto == export_cluster.prototype:
                msg = 'can not multi bind {} to {}'
                err('BIND_ERROR', msg.format(proto_ref(source_proto), obj_ref(cluster)))


def bind_service(cluster, service, export_cluster, export_service):
    if service.id == export_service.id:
        err('BIND_ERROR', 'can not bind service to themself')
    if not PrototypeExport.objects.filter(prototype=export_service.prototype):
        err('BIND_ERROR', '{} do not have exports'.format(obj_ref(service)))
    imports = PrototypeImport.objects.filter(prototype=service.prototype)
    if not imports:
        err('BIND_ERROR', '{} do not have imports'.format(proto_ref(service.prototype)))
    actual_import = None
    for imp in imports:
        if export_service.prototype.name == imp.name:
            actual_import = imp
    if not actual_import:
        msg = 'Export {} does not match import names'
        err('BIND_ERROR', msg.format(proto_ref(export_service.prototype)))

    check_multi_bind(actual_import, cluster, service, export_cluster, export_service)
    # To do: check versions
    try:
        with transaction.atomic():
            cbind = ClusterBind(
                cluster=cluster,
                service=service,
                source_cluster=export_cluster,
                source_service=export_service
            )
            cbind.save()
            cm.issue.save_issue(cbind.cluster)
    except IntegrityError:
        err('BIND_ERROR', 'service already binded')
    return {
        'id': cbind.id,
        'export_cluster_id': export_cluster.id,
        'export_cluster_name': export_cluster.name,
        'export_cluster_prototype_name': export_cluster.prototype.name,
        'export_service_id': export_service.id,
        'export_service_name': export_service.prototype.name,
    }


def push_obj(obj, state):
    if obj.stack:
        stack = json.loads(obj.stack)
    else:
        stack = []

    if not stack:
        stack = [state]
    else:
        stack[0] = state
    obj.stack = json.dumps(stack)
    obj.save()
    return obj


def set_object_state(obj, state):
    obj.state = state
    obj.save()
    cm.status_api.set_obj_state(obj.prototype.type, obj.id, state)
    log.info('set %s state to "%s"', obj_ref(obj), state)
    return obj


def set_cluster_state(cluster_id, state):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        msg = 'Cluster # {} does not exist'
        err('CLUSTER_NOT_FOUND', msg.format(cluster_id))
    return push_obj(cluster, state)


def set_host_state(host_id, state):
    try:
        host = Host.objects.get(id=host_id)
    except Host.DoesNotExist:
        msg = 'Host # {} does not exist'
        err('HOST_NOT_FOUND', msg.format(host_id))
    return push_obj(host, state)


def set_provider_state(provider_id, state):
    try:
        provider = HostProvider.objects.get(id=provider_id)
    except HostProvider.DoesNotExist:
        msg = 'Host Provider # {} does not exist'
        err('PROVIDER_NOT_FOUND', msg.format(provider_id))
    if provider.state == config.Job.LOCKED:
        return push_obj(provider, state)
    else:
        return set_object_state(provider, state)


def set_service_state(cluster_id, service_name, state):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        msg = 'Cluster # {} does not exist'
        err('CLUSTER_NOT_FOUND', msg.format(cluster_id))
    try:
        proto = Prototype.objects.get(
            type='service',
            name=service_name,
            bundle=cluster.prototype.bundle
        )
    except Prototype.DoesNotExist:
        msg = 'Service "{}" does not exist'
        err('SERVICE_NOT_FOUND', msg.format(service_name))
    try:
        obj = ClusterObject.objects.get(cluster=cluster, prototype=proto)
    except ClusterObject.DoesNotExist:
        msg = '{} does not exist in cluster # {}'
        err('OBJECT_NOT_FOUND', msg.format(proto_ref(proto), cluster.id))
    return push_obj(obj, state)


def set_service_state_by_id(cluster_id, service_id, state):
    try:
        obj = ClusterObject.objects.get(
            id=service_id, cluster__id=cluster_id, prototype__type='service'
        )
    except ClusterObject.DoesNotExist:
        msg = 'service # {} does not exist in cluster # {}'
        err('OBJECT_NOT_FOUND', msg.format(service_id, cluster_id))
    return push_obj(obj, state)
