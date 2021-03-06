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
import { Component, EventEmitter, Input, Output, QueryList, ViewChildren } from '@angular/core';
import { FormGroup } from '@angular/forms';

import { FieldService } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { IConfig, PanelOptions, FieldOptions } from '../types';

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let item of dataOptions; trackBy: trackBy">
      <app-group-fields *ngIf="panelsOnly(item); else more" [panel]="item" [form]="form"></app-group-fields>
      <ng-template #more>
        <app-field *ngIf="!item.hidden" class="alone" [form]="form" [options]="item" [ngClass]="{ 'read-only': item.disabled }"></app-field>
      </ng-template>
    </ng-container>
  `
})
export class ConfigFieldsComponent {
  dataOptions: (FieldOptions | PanelOptions)[] = [];
  form = new FormGroup({});

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  shapshot: any;

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  @Input()
  set model(data: IConfig) {
    this.dataOptions = this.service.getPanels(data);
    this.form = this.service.toFormGroup(this.dataOptions);
    this.shapshot = { ...this.form.value };
    this.event.emit({ name: 'load', data: { form: this.form } });
  }

  constructor(private service: FieldService) {}

  panelsOnly(item: FieldOptions | PanelOptions) {
    return 'options' in item && !item.hidden;
  }

  trackBy(index: number, item: PanelOptions): string {
    return item.name;
  }
}
