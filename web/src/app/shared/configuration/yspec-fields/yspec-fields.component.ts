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
import { Component, OnInit, Input } from '@angular/core';
import { FieldOptions } from '../types';
import { FormGroup, FormControl } from '@angular/forms';
import { YspecService } from './yspec.service';
import { FieldService } from '../field.service';

@Component({
  selector: 'app-yspec-fields',
  templateUrl: './yspec-fields.component.html',
  styleUrls: ['./yspec-fields.component.scss'],
})
export class YspecFieldsComponent implements OnInit {
  @Input()
  options: FieldOptions;
  @Input()
  form: FormGroup;

  output: FieldOptions[];
  schemeFormGroup = new FormGroup({});

  constructor(private yspec: YspecService, private field: FieldService) {}

  ngOnInit() {
    this.output = this.yspec.prepare(this.options);

    this.output.forEach(field => {
      this.schemeFormGroup.setControl(field.key, new FormControl({ value: field.value, disabled: false }, this.field.setValidator(field)));
    });

    this.form.setControl(this.options.key, this.schemeFormGroup);
    
  }
}
