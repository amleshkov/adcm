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
import { Component, OnInit } from '@angular/core';
import { ClusterService } from '@app/core';

@Component({
  selector: 'app-cluster-host',
  template: `
    <app-add-button [name]="'host2cluster'" class="add-button">Add hosts</app-add-button>
    <app-list class="main" [appBaseList]="'host2cluster'"></app-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:absolute; right: 20px;top:10px;}'],
})
export class HostComponent {}

@Component({
  selector: 'app-services',
  template: `
    <app-add-button [name]="'service'" class="add-button">Add service</app-add-button>
    <app-list class="main" [appBaseList]="'service2cluster'" appActionHandler></app-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:absolute; right: 20px;top:10px;}'],
})
export class ServicesComponent {}

@Component({
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ path: '/cluster', name: 'clusters' }]"></app-crumbs>
      <span class="example-spacer"></span>
      <app-add-button [name]="typeName" (added)="list.current = $event">Create {{ typeName }}</app-add-button>
    </mat-toolbar>
    <div class="container-entry">
      <app-list #list class="main" appActionHandler [appBaseList]="typeName"></app-list>
    </div>
  `,
})
export class ClusterListComponent {
  typeName = 'cluster';
}

@Component({
  template: `
    <app-service-host [cluster]="cluster"></app-service-host>
  `,
  styles: [':host { flex: 1; }'],
})
export class HcmapComponent implements OnInit {
  cluster: { id: number; hostcomponent: string };
  constructor(private service: ClusterService) {}

  ngOnInit() {
    const { id, hostcomponent } = { ...this.service.Cluster };
    this.cluster = { id, hostcomponent };
  }
}
