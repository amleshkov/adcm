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
import { Constraint } from '@app/core/types';

export type ActionParam = 'add' | 'remove';

export interface Post {
  id?: number;
  host_id: number;
  service_id: number;
  component_id: number;
}

export class Post implements Post {
  constructor(public host_id: number, public service_id: number, public component_id: number, public id?: number) {}
}

export class Tile {
  id: number;
  name: string;
  relations: Tile[] = [];
  isSelected?: boolean;
  isLink?: boolean;
  limit?: Constraint;
  disabled: boolean;
  actions?: ActionParam[];
}

export class HostTile extends Tile {
  constructor(public id: number, public name: string) {
    super();
  }
}

export class CompTile extends Tile {
  constructor(public id: number, public service_id: number, public name: string, public limit: any, public disabled = false, public actions?: ActionParam[]) {
    super();
  }
}

export class StatePost {
  private _data: Post[];

  constructor() {
    this._data = [];
  }

  private _compare(a: Post, b: Post) {
    return a.host_id === b.host_id && a.service_id === b.service_id && a.component_id === b.component_id;
  }

  get data() {
    return this._data;
  }

  add(post: Post) {
    const f = this._data.find(p => this._compare(p, post));
    if (!f) this._data.push(post);
    else if (!f.id) f.id = post.id;
  }

  delete(post: Post) {
    this._data = this._data.filter(p => !this._compare(p, post));
  }

  clear() {
    this._data = [];
  }

  update(data: Post[]) {
    data.forEach(a => this.add(new Post(a.host_id, a.service_id, a.component_id, a.id)));
  }
}

export class Stream {
  target: Tile;
  link: Tile;
  linkSource: Tile[];
  selected: Tile;
  constructor() {}
}
