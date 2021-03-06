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

import os
import json

import cm.config as config
from cm.logger import log
from cm.adcm_config import get_prototype_config, cook_file_type_name
from cm.models import Cluster, ClusterObject, ServiceComponent, HostComponent, Host, ConfigLog
from cm.models import ClusterBind, PrototypeExport, HostProvider, Prototype, PrototypeImport


def process_config(obj, conf, attr=None):
    spec, _, _, _ = get_prototype_config(obj.prototype)
    for key in conf:
        if 'type' in spec[key]:
            if spec[key]['type'] == 'file' and conf[key] is not None:
                conf[key] = cook_file_type_name(obj, key, '')
        else:
            for subkey in conf[key]:
                if spec[key][subkey]['type'] == 'file' and conf[key][subkey] is not None:
                    conf[key][subkey] = cook_file_type_name(obj, key, subkey)
    if attr:
        for key, val in json.loads(attr).items():
            if 'active' in val and not val['active']:
                conf[key] = None
    return conf


def get_import(cluster):   # pylint: disable=too-many-branches
    def get_actual_import(bind, obj):
        if bind.service:
            proto = bind.service.prototype
        else:
            proto = bind.cluster.prototype
        return PrototypeImport.objects.get(prototype=proto, name=obj.prototype.name)

    imports = {}
    for obj in [cluster] + [o for o in ClusterObject.objects.filter(cluster=cluster)]:   # pylint: disable=unnecessary-comprehension
        for imp in PrototypeImport.objects.filter(prototype=obj.prototype):
            if imp.default:
                if imp.multibind:
                    imports[imp.name] = []
                else:
                    imports[imp.name] = {}
                for group in json.loads(imp.default):
                    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
                    conf = process_config(obj, json.loads(cl.config), cl.attr)
                    if imp.multibind:
                        imports[imp.name].append({group: conf[group]})
                    else:
                        imports[imp.name][group] = conf[group]

    first = True
    for bind in ClusterBind.objects.filter(cluster=cluster):
        if bind.source_service:
            obj = bind.source_service
        else:
            obj = bind.source_cluster
        conf_ref = obj.config
        export_proto = obj.prototype
        cl = ConfigLog.objects.get(obj_ref=conf_ref, id=conf_ref.current)
        conf = process_config(obj, json.loads(cl.config), cl.attr)
        actual_import = get_actual_import(bind, obj)
        if actual_import.multibind:
            if export_proto.name not in imports:
                imports[export_proto.name] = []
            elif actual_import.default and first:
                imports[export_proto.name] = []
                first = False
        else:
            imports[export_proto.name] = {}
        for export in PrototypeExport.objects.filter(prototype=export_proto):
            if actual_import.multibind:
                imports[export_proto.name].append({export.name: conf[export.name]})
            else:
                imports[export_proto.name][export.name] = conf[export.name]
    return imports


def get_obj_config(obj):
    if obj.config is None:
        return {}
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    js_conf = json.loads(cl.config)
    return process_config(obj, js_conf, cl.attr)


def get_cluster_config(cluster_id):
    cluster = Cluster.objects.get(id=cluster_id)
    res = {
        'cluster': {
            'config': get_obj_config(cluster),
            'name': cluster.name,
            'id': cluster.id,
        },
        'services': {},
    }
    imports = get_import(cluster)
    if imports:
        res['cluster']['imports'] = imports
    for service in ClusterObject.objects.filter(cluster=cluster):
        res['services'][service.prototype.name] = {'config': get_obj_config(service)}
        for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
            res['services'][service.prototype.name][component.component.name] = {
                'component_id': component.id
            }
    return res


def get_provider_config(provider_id):
    provider = HostProvider.objects.get(id=provider_id)
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
    return {
        'provider': {
            'config': get_obj_config(provider),
            'name': provider.name,
            'id': provider.id,
            'host_prototype_id': host_proto.id,
        }
    }


def get_host_groups(cluster_id, delta):
    groups = {}
    cluster = Cluster.objects.get(id=cluster_id)
    all_hosts = HostComponent.objects.filter(cluster=cluster)
    for hc in all_hosts:
        key = '{}.{}'.format(hc.service.prototype.name, hc.component.component.name)
        if key not in groups:
            groups[key] = {'hosts': {}}
        groups[key]['hosts'][hc.host.fqdn] = get_obj_config(hc.host)
    for hc in all_hosts:
        key = '{}'.format(hc.service.prototype.name)
        if key not in groups:
            groups[key] = {'hosts': {}}
        groups[key]['hosts'][hc.host.fqdn] = get_obj_config(hc.host)

    for htype in delta:
        for key in delta[htype]:
            lkey = '{}.{}'.format(key, htype)
            if lkey not in groups:
                groups[lkey] = {'hosts': {}}
            for fqdn in delta[htype][key]:
                host = delta[htype][key][fqdn]
                groups[lkey]['hosts'][host.fqdn] = get_obj_config(host)

    return groups


def get_hosts(host_list):
    group = {}
    for host in host_list:
        group[host.fqdn] = get_obj_config(host)
        group[host.fqdn]['adcm_hostid'] = host.id
    return group


def get_cluster_hosts(cluster_id):
    return {'CLUSTER': {
        'hosts': get_hosts(Host.objects.filter(cluster__id=cluster_id)),
        'vars': get_cluster_config(cluster_id)
    }}


def get_provider_hosts(provider_id):
    return {'PROVIDER': {
        'hosts': get_hosts(Host.objects.filter(provider__id=provider_id)),
        'vars': get_provider_config(provider_id)
    }}


def get_host(host_id):
    host = Host.objects.get(id=host_id)
    groups = {'HOST': {'hosts': get_hosts([host])}}
    groups.update(get_provider_hosts(host.provider.id))
    return groups


def prepare_job_inventory(selector, job_id, delta):
    log.info('prepare inventory for job #%s, selector: %s', job_id, selector)
    fd = open(os.path.join(config.RUN_DIR, f'{job_id}-inventory.json'), 'w')
    inv = {'all': {'children': {}}}
    if 'cluster' in selector:
        inv['all']['children'].update(get_cluster_hosts(selector['cluster']))
        inv['all']['children'].update(get_host_groups(selector['cluster'], delta))
    if 'host' in selector:
        inv['all']['children'].update(get_host(selector['host']))
    if 'provider' in selector:
        inv['all']['children'].update(get_provider_hosts(selector['provider']))
    json.dump(inv, fd, indent=3)
    fd.close()
