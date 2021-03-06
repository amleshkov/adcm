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
import { Component, ComponentFactoryResolver, EventEmitter, Inject, OnInit, Type, ViewChild } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { DynamicComponent, DynamicDirective, DynamicEvent } from '../directives/dynamic.directive';
import { ChannelService } from '@app/core';

export interface DialogData {
  title: string;
  component: Type<any>;
  model?: any;
  event?: EventEmitter<any>;
  text?: string;  
  controls?: any[];
  disabled?: boolean;
}

@Component({
  selector: 'app-dialog',
  template: `
    <h3 mat-dialog-title [style.marginBottom.px]="10">{{ data.title || 'Notification' }}</h3>
    <mat-dialog-content class="content" appScroll (read)="scroll($event)">
      <div *ngIf="data.text" [innerHTML]="data.text | breakRow"></div>
      <ng-template appDynamic></ng-template>
    </mat-dialog-content>
    <mat-dialog-actions *ngIf="data.controls" style="text-align: right;">
      <button mat-raised-button color="primary" [mat-dialog-close]="true" [disabled]="data?.disabled" tabindex="2">
        {{ data.controls[0] }}
      </button>
      <button mat-button (click)="_noClick()" tabindex="-1">{{ data.controls[1] }}</button>
    </mat-dialog-actions>
  `,
})
export class DialogComponent implements OnInit {
  controls: string[];
  noClose: boolean | undefined;

  @ViewChild(DynamicDirective, { static: true }) dynamic: DynamicDirective;

  constructor(
    public dialogRef: MatDialogRef<DialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private componentFactoryResolever: ComponentFactoryResolver,
    private channel: ChannelService
  ) {}

  ngOnInit(): void {
    if (this.data.component) {
      const componentFactory = this.componentFactoryResolever.resolveComponentFactory(this.data.component);
      const viewContainerRef = this.dynamic.viewContainerRef;
      viewContainerRef.clear();

      const componentRef = viewContainerRef.createComponent(componentFactory);
      const instance = <DynamicComponent>componentRef.instance;
      instance.model = this.data.model;
      // event define in the component
      if (instance.event) instance.event.subscribe((e: DynamicEvent) => this.dialogRef.close(e));

      if (this.data.event) instance.event = this.data.event;
    }
  }

  scroll(stop: { direct: -1 | 1 | 0, screenTop: number }) {
    this.channel.next('scroll', stop);
  }

  _noClick(): void {
    this.dialogRef.close();
  }
}
