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
from unittest.mock import patch, Mock, mock_open

from django.test import TestCase
from django.utils import timezone

import cm.config as config
import job_runner
import task_runner
from cm.logger import log
from cm.models import TaskLog, JobLog


class PreparationData:

    def __init__(self, number_tasks, number_jobs):
        self.number_tasks = number_tasks
        self.number_jobs = number_jobs
        self.tasks = []
        self.jobs = []
        self.to_prepare()

    def to_prepare(self):
        for task_id in range(1, self.number_tasks + 1):
            task_log_data = {
                'action_id': task_id,
                'object_id': task_id,
                'pid': task_id,
                'selector': {'cluster': task_id},
                'status': 'success',
                'config': '',
                'hostcomponentmap': '',
                'start_date': timezone.now(),
                'finish_date': timezone.now()
            }
            self.tasks.append(TaskLog.objects.create(**task_log_data))
            for jn in range(1, self.number_jobs + 1):
                job_log_data = {
                    'task_id': task_id,
                    'action_id': task_id,
                    'pid': jn + 1,
                    'selector': {'cluster': task_id},
                    'status': 'success',
                    'start_date': timezone.now(),
                    'finish_date': timezone.now()
                }
                self.jobs.append(JobLog.objects.create(**job_log_data))

    def get_task(self, _id):
        return self.tasks[_id - 1]

    def get_job(self, _id):
        return self.jobs[_id - 1]


class TestTaskRunner(TestCase):

    def setUp(self):
        log.debug = Mock()
        log.error = Mock()
        log.info = Mock()

    @patch('builtins.open')
    def test_open_file(self, _mock_open):
        file_path = "{}/{}-{}.txt".format('root', 'tag', 1)
        task_runner.open_file('root', 1, 'tag')
        _mock_open.assert_called_once_with(file_path, 'w')

    @patch('subprocess.Popen')
    def test_run_job(self, mock_subprocess_popen):
        process_mock = Mock()
        attrs = {'wait.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subprocess_popen.return_value = process_mock
        code = task_runner.run_job(1, 1, '', '')
        self.assertEqual(code, 0)

    @patch('task_runner.open_file')
    @patch('cm.job.set_task_status')
    @patch('cm.job.re_prepare_job')
    @patch('task_runner.run_job')
    @patch('cm.job.finish_task')
    def test_run_task(self, mock_finish_task, mock_run_job, mock_re_prepare_job,
                      mock_set_task_status, mock_open_file):
        mock_run_job.return_value = 0
        _file = Mock()
        mock_open_file.return_value = _file

        pd = PreparationData(1, 1)
        task_runner.run_task(1)
        task = pd.get_task(1)
        job = pd.get_job(1)

        mock_finish_task.assert_called_once_with(task, job, config.Job.SUCCESS)
        mock_run_job.assert_called_once_with(task.id, job.id, _file, _file)
        mock_re_prepare_job.assert_not_called()
        mock_set_task_status.assert_called_once_with(task, config.Job.RUNNING)
        self.assertTrue(JobLog.objects.get(id=1).start_date != job.start_date)

    @patch('task_runner.run_task')
    @patch('sys.exit')
    def test_do(self, mock_exit, mock_run_task):
        with patch('sys.argv', [__file__, 1]):
            task_runner.do()
            self.assertEqual(mock_exit.call_count, 0)
            mock_run_task.assert_called_once_with(1)


class TestJobRunner(TestCase):

    def setUp(self):
        log.info = Mock()
        log.debug = Mock()
        log.error = Mock()

    @patch('builtins.open')
    def test_open_file(self, _mock_open):
        file_path = "{}/{}-{}.txt".format('root', 'tag', 1)
        job_runner.open_file('root', 1, 'tag')
        _mock_open.assert_called_once_with(file_path, 'w')

    @patch('json.load')
    @patch('builtins.open', create=True)
    def test_read_config(self, _mock_open, mock_json):
        _mock_open.side_effect = mock_open(read_data='').return_value
        mock_json.return_value = {}
        conf = job_runner.read_config(1)
        file_name = '{}/{}-config.json'.format(config.RUN_DIR, 1)
        _mock_open.assert_called_once_with(file_name)
        self.assertDictEqual(conf, {})

    @patch('cm.job.set_job_status')
    def test_set_job_status(self, mock_set_job_status):
        mock_set_job_status.return_value = None
        code = job_runner.set_job_status(1, 0, 1)
        self.assertEqual(code, 0)
        mock_set_job_status.assert_called_once_with(1, config.Job.SUCCESS, 1)

    def test_set_pythonpath(self):
        cmd_env = os.environ.copy()
        python_paths = filter(
            lambda x: x != '',
            ['./pmod'] + cmd_env.get('PYTHONPATH', '').split(':'))
        cmd_env['PYTHONPATH'] = ':'.join(python_paths)
        self.assertDictEqual(cmd_env, job_runner.set_pythonpath())

    @patch('cm.job.set_job_status')
    @patch('sys.exit')
    @patch('job_runner.set_job_status')
    @patch('job_runner.set_pythonpath')
    @patch('subprocess.Popen')
    @patch('os.chdir')
    @patch('job_runner.open_file')
    @patch('job_runner.read_config')
    def test_run_ansible(  # pylint: disable=too-many-arguments
            self, mock_read_config, mock_open_file, mock_chdir, mock_subprocess_popen,
            mock_set_pythonpath, mock_set_job_status, mock_exit, mock_job_set_job_status):
        conf = {
            'job': {'playbook': 'test'},
            'env': {'stack_dir': 'test'}
        }
        mock_read_config.return_value = conf
        _file = Mock()
        mock_open_file.return_value = _file
        process_mock = Mock()
        process_mock.pid = 1
        attrs = {'wait.return_value': 0}
        process_mock.configure_mock(**attrs)
        mock_subprocess_popen.return_value = process_mock
        python_path = Mock()
        mock_set_pythonpath.return_value = python_path

        job_runner.run_ansible(1)

        mock_read_config.assert_called_once_with(1)

        self.assertEqual(mock_open_file.call_count, 2)
        mock_open_file.assert_any_call(config.LOG_DIR, 'ansible-out', 1)
        mock_open_file.assert_any_call(config.LOG_DIR, 'ansible-err', 1)

        mock_chdir.assert_called_with(conf['env']['stack_dir'])

        mock_set_job_status.assert_called_once_with(1, 0, 1)
        mock_subprocess_popen.assert_called_once_with(
            [
                'ansible-playbook',
                '-e',
                '@{}/{}-config.json'.format(config.RUN_DIR, 1),
                '-i',
                '{}/{}-inventory.json'.format(config.RUN_DIR, 1),
                conf['job']['playbook']
            ], env=python_path, stdout=_file, stderr=_file)
        self.assertEqual(mock_set_pythonpath.call_count, 1)
        self.assertEqual(mock_exit.call_count, 1)
        mock_job_set_job_status.assert_called_with(1, config.Job.RUNNING, 1)

    @patch('job_runner.run_ansible')
    @patch('sys.exit')
    def test_do(self, mock_exit, mock_run_ansible):
        with patch('sys.argv', [__file__, 1]):
            job_runner.do()
            self.assertEqual(mock_exit.call_count, 0)
            self.assertEqual(mock_run_ansible.call_count, 1)
            mock_run_ansible.assert_called_once_with(1)
