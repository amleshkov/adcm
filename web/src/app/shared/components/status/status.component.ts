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
import { Component, OnDestroy, OnInit, QueryList, ViewChildren } from '@angular/core';
import { MatExpansionPanel, MatSelectChange } from '@angular/material';
import { EventMessage, SocketState } from '@app/core/store';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { map, switchMap, tap } from 'rxjs/operators';

import { SocketListener } from '../../directives/base.directive';
import { StatusInfo, StatusService } from './status.service';
import { ClusterService } from '@app/core';

@Component({
  selector: 'app-status',
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.scss'],
  // changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusComponent extends SocketListener implements OnInit, OnDestroy {
  statusInfo$: Observable<StatusInfo[]>;
  hcm: StatusInfo[] = [];
  view: 'host' | 'service' = 'service';
  showChangeView = false;
  listIcon: 'list' | 'view_list' = 'view_list';
  listTooltip = 'Expand all';
  loadString = 'Loading...';

  @ViewChildren(MatExpansionPanel) panels: QueryList<MatExpansionPanel>;

  constructor(private service: StatusService, private details: ClusterService, socket: Store<SocketState>) {
    super(socket);
  }

  ngOnInit() {
    this.details.worker$.pipe(this.takeUntil()).subscribe(() => this.init());
  }

  socketListener(e: EventMessage) {
    if (
      (e.event === 'remove' &&
        e.object.details.type === 'cluster' &&
        'cluster_id' in this.details.Current &&
        +e.object.details.value === this.details.Current.cluster_id) ||
      e.event === 'change_hostcomponentmap'
    )
      this.init();
    if (e.event === 'change_status') this.change_status(e);
  }

  toggleExpand() {
    const flag = this.listIcon === 'list';
    if (flag) {
      this.listIcon = 'view_list';
      this.listTooltip = 'Expand all';
    } else {
      this.listIcon = 'list';
      this.listTooltip = 'Collapse all';
    }
    this.panels.forEach(p => (p.expanded = this.listIcon === 'list'));
  }

  changeView(matSelectChange: MatSelectChange) {
    this.listIcon = 'view_list';
    this.view = matSelectChange.value;
    this.getStatusInfo();
  }

  getStatusInfo(rid?: number) {
    const { id, hostcomponent } = { ...this.details.Cluster };

    if (!this.details.Cluster) {
      if ('cluster_id' in this.details.Current && this.details.Current.cluster_id) {
        this.statusInfo$ = this.service
          .getClusterById(this.details.Current.cluster_id)
          .pipe(switchMap(cluster => this.service.getStatusInfo(cluster.id, cluster.hostcomponent).pipe(map(a => this.service.fillStatus(a, id)))))
          .pipe(tap(hcm => (this.hcm = hcm)));
      } else this.loadString = 'Nothing to display.';
    } else
      this.statusInfo$ = this.service
        .getStatusInfo(id, hostcomponent)
        .pipe(map(a => (this.view === 'host' ? this.service.fillStatus(a, rid) : this.service.fillStatusByService(a, rid))))
        .pipe(tap(hcm => (this.hcm = hcm)));
  }

  change_status(e: EventMessage) {
    if (e.object.type === 'host') {
      const c = this.hcm.find(h => h.id === e.object.id);
      if (c) c.status = +e.object.details.value;

      this.hcm.forEach(a => {
        const fh = a.relations.find(h => h.id === e.object.id);
        if (fh) fh.status = +e.object.details.value;
      });
    }

    if (e.object.type === 'service') {
      const c = this.hcm.filter(h => h.relations.find(co => co.id === e.object.id));
      if (c) {
        c.forEach(ho => {
          const f = ho.relations.find(co => co.id === e.object.id);
          if (f) f.status = +e.object.details.value;
        });
      }
    }

    if (e.object.type === 'hostcomponent') {
      const host_id = e.object.id,
        component_id = +e.object.details.id;
      if (this.hcm.length) {
        const c = this.hcm.find(h => h.id === host_id).relations.find(s => s.components.some(co => co.id === component_id));
        if (c) {
          const f = c.components.find(co => co.id === component_id);
          if (f) f.status = +e.object.details.value;
        }
      }
      const sc = this.hcm.find(co => co.id === component_id);
      if (sc) sc.status = +e.object.details.value;
    }
    if (this.hcm.length) this.statusInfo$ = of(this.hcm);
  }

  init() {
    const { id, typeName } = { ...this.details.Current };
    switch (typeName) {
      case 'cluster':
        this.showChangeView = true;
        this.getStatusInfo();
        break;
      case 'service':
        this.view = 'service';
        this.getStatusInfo(id);
        break;
      case 'host':
        this.view = 'host';
        this.getStatusInfo(id);
        break;
    }
  }
}
