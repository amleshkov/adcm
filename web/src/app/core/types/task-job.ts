// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { ApiBase } from './api';

export type JobStatus = 'created' | 'running' | 'failed' | 'success';

interface TaskBase {
  start_date: string;  
  finish_date: string;
  objects: { id: number; name: string; type: string }[];  
  status: JobStatus;
  action: JobAction;
}

export interface JobAction {
  prototype_name?: string;
  prototype_version?: string;
  bundle_id?: string;
  display_name: string;
}
interface JobRaw extends TaskBase {  
  log_files: LogFile[];
}

export interface TaskRaw extends TaskBase {
  jobs: Job[];
}

export type Job = JobRaw & ApiBase;
export type Task = TaskRaw & ApiBase;

export interface LogFile {
  level: string;
  host: string;
  tag: string;
  type: string;
  file: string;
  url: string;
}

export interface Log {
  content: string | CheckLog[];
  fileName: string;
}

export interface CheckLog {
  title: string;
  message: string;
  result: boolean;
}
