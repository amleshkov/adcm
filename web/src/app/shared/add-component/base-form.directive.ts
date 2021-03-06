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
import { Directive, EventEmitter, OnDestroy, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { Entities } from '@app/core/types';

import { BaseDirective } from '../directives/base.directive';
import { AddService } from './add.service';

@Directive({
  selector: '[appBaseForm]',
})
export class BaseFormDirective extends BaseDirective implements OnDestroy {
  @Output() cancel = new EventEmitter<Entities>();
  form: FormGroup;

  constructor(public service: AddService) {
    super();
  }

  onCancel(result?: Entities, reset = true) {
    if (this.form && reset) this.form.reset();
    this.cancel.emit(result);
  }
}
