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
import { Directive, HostListener, Input } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { IAction } from '@app/core/types';
import { DialogComponent } from '../dialog.component';
import { ActionMasterComponent } from './master/master.component';

export interface ActionParameters {
  cluster?: {
    id: number;
    hostcomponent: string;
  };
  actions: IAction[];
}

@Directive({
  selector: '[appActions]',
})
export class ActionsDirective {
  @Input('appActions')
  data: ActionParameters;

  constructor(private dialog: MatDialog) {}

  @HostListener('click')
  onClick() {
    const flag = this.data.actions[0].config.config.length || this.data.actions[0].hostcomponentmap;
    this.dialog.open(DialogComponent, {
      width: flag ? '90%' : '400px',
      maxWidth: '1400px',
      data: {
        title: 'Run an action?',
        component: ActionMasterComponent,
        model: this.data,
      },
    });
  }
}
