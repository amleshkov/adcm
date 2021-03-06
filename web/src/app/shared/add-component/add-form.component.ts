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
import { Component } from '@angular/core';
import { DynamicComponent } from '@app/shared/directives';

import { FormModel } from './add.service';
import { Entities } from '@app/core/types/api';

@Component({
  selector: 'app-add-form',
  template: `
    <div [style.minWidth.px]="450">
      <ng-container [ngSwitch]="model.name">
        <ng-container *ngSwitchCase="'provider'">
          <app-add-provider (cancel)="hideForm()"></app-add-provider>
        </ng-container>
        <ng-container *ngSwitchCase="'host'">
          <app-add-host (cancel)="hideForm()"></app-add-host>
        </ng-container>
        <ng-container *ngSwitchCase="'cluster'">
          <app-add-cluster (cancel)="hideForm()"></app-add-cluster>
        </ng-container>
        <ng-container *ngSwitchCase="'service'">
          <app-add-service (cancel)="hideForm()"></app-add-service>
        </ng-container>
        <ng-container *ngSwitchCase="'host2cluster'">
          <app-add-host2cluster (cancel)="hideForm($event)"></app-add-host2cluster>
        </ng-container>
      </ng-container>
    </div>
  `,
})
export class AddFormComponent implements DynamicComponent {
  model: FormModel;
  hideForm(result?: Entities) {
    if (!result) this.model.success.emit();
  }
}
