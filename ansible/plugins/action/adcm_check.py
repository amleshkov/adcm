#!/usr/bin/python
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

# pylint: disable=wrong-import-position,unused-import

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_check
short_description: add entry to json log file
description:
    - The C(adcm_check) module is intended to log result of some checks to structured JSON log file.
      This log can be seen via ADCM user interface. Each invoke of C(adcm_check) add one entry to
      json log file linked with ADCM job. You can invoke C(adcm_check) with one job id any number of
      time per playbook.
options:
  title:
    description:
      - Name of check
    required: yes
  result:
    description:
      - Result of check, yes/no
    required: yes
    type: bool
  msg:
   description:
      - Description of check or results of check
'''

EXAMPLES = r'''
 - name: memory check
   adcm_check:
     title: "Memory check"
     msg: "640K is ok for everyone"
     result: yes
'''

RETURN = r'''
result:
  check: JSON log of all checks for this ADCM job
'''

import sys
from ansible.plugins.action import ActionBase

sys.path.append('/adcm')
import adcm.init_django
import cm.job
from cm.errors import AdcmEx
from cm.logger import log


class ActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('title', 'result', 'msg'))

    def run(self, tmp=None, task_vars=None):
        job_id = None
        if task_vars is not None and 'job' in task_vars or 'id' in task_vars['job']:
            job_id = task_vars['job']['id']

        result = super(ActionModule, self).run(tmp, task_vars)

        if ('title' not in self._task.args or
                'result' not in self._task.args or
                'msg' not in self._task.args):
            return {"failed": True, "msg": "title, result and msg are mandatory args of adcm_check"}
        result = super(ActionModule, self).run(tmp, task_vars)
        title = self._task.args['title']
        result = self._task.args['result']
        msg = self._task.args['msg']

        log.debug('ansible adcm_check: %s, %s, %s, %s', job_id, title, result, msg)

        try:
            cm.job.log_check(job_id, title, result, msg)
        except AdcmEx as e:
            return {"failed": True, "msg": e.code + ":" + e.msg}

        return {"failed": False, "changed": False}
