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
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { Tile } from '../types';

@Component({
  selector: 'app-much-2-many',
  templateUrl: './much-2-many.component.html',
  styleUrls: ['./much-2-many.component.scss'],
})
export class Much2ManyComponent {
  isShow = false;

  @Output() clickToTitleEvt: EventEmitter<any> = new EventEmitter();
  @Output() clearRelationEvt: EventEmitter<any> = new EventEmitter();
  @Input() model: Tile;

  isDisabled() {
    if (this.model.actions) return !this.model.actions.length; //.every(e => e !== 'add');
    return this.model.disabled;
  }

  clearDisabled(rel: Tile) {
    if (this.model.actions) return this.model.actions.every(e => e !== 'remove');
    return rel.disabled || this.model.disabled;
  }

  clickToTitle() {
    this.clickToTitleEvt.emit(this.model);
  }

  toggleRelations() {
    this.isShow = !this.isShow;
  }

  clearRelation(rel: Tile) {
    this.model.relations = this.model.relations.filter(a => a !== rel);
    this.clearRelationEvt.emit({ rel: rel, model: this.model });
  }

  checkLimit(): boolean {
    return !!this.model.limit && Array.isArray(this.model.limit) && !!this.model.limit.length;
  }

  setNotify() {
    const a = this.model.limit[0],
      b = this.model.limit[1];
    return `${this.model.relations.length}/${b !== '+' && b ? b : false || a} ${b && b === '+' ? '+' : ''}`;
  }
}
