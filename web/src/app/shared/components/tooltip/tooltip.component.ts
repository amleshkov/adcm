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
import { Component, ElementRef, EventEmitter, HostListener, Injector, Input, OnDestroy, OnInit, Renderer2, Type } from '@angular/core';
import { Router } from '@angular/router';
import { BaseDirective } from '@app/shared/directives';
import { delay, take } from 'rxjs/operators';

import { IssueInfoComponent } from '../issue-info.component';
import { StatusInfoComponent } from '../status-info.component';
import { ComponentData, TooltipOptions, TooltipService } from './tooltip.service';

const POSITION_MARGIN = 20;

@Component({
  selector: 'app-simple-text',
  template: '{{ current }}'
})
export class SimpleTextComponent implements OnInit {
  @Input() current: any;
  constructor(private componentData: ComponentData) {}
  ngOnInit(): void {
    this.current = this.current || this.componentData.current;
    this.componentData.emitter.emit('Done');
  }
}

@Component({
  selector: 'app-tooltip',
  template: '<ng-container *ngComponentOutlet="CurrentComponent; injector: componentInjector"></ng-container>',
  styleUrls: ['./tooltip.component.scss']
})
export class TooltipComponent extends BaseDirective implements OnInit, OnDestroy {
  private options: TooltipOptions;
  source: HTMLElement;

  CurrentComponent: Type<SimpleTextComponent | IssueInfoComponent | StatusInfoComponent>;
  componentInjector: Injector;

  constructor(private el: ElementRef, private service: TooltipService, private renderer: Renderer2, private router: Router, private parentInjector: Injector) {
    super();
  }

  @HostListener('mouseenter', ['$event']) menter() {
    this.service.mouseEnterTooltip();
  }

  @HostListener('mouseleave') mleave() {
    this.service.mouseLeaveTooltip();
  }

  ngOnInit(): void {
    this.service.position$.pipe(this.takeUntil()).subscribe(o => {
      if (o) {
        this.clear();
        this.buildComponent(o);
      } else this.hide();
    });
  }

  hide() {
    this.renderer.setAttribute(this.el.nativeElement, 'style', `opacity: 0; height: auto;`);
    this.clear();
  }

  clear() {
    if (this.source) {
      this.source = null;
      this.CurrentComponent = null;
    }
  }

  position() {
    const o = this.options;
    const el = this.el.nativeElement;
    const bodyWidth = document.querySelector('body').offsetWidth,
      bodyHeight = (document.getElementsByTagName('app-root')[0] as HTMLElement).offsetHeight,
      eLeft = o.event.x - el.offsetWidth,
      eRight = o.event.x + el.offsetWidth,
      eTop = o.event.y - el.offsetHeight,
      eBottom = o.event.y + el.offsetHeight;
    const position: any = { left: '', top: '', bottom: '', right: '', height: '' };

    this.renderer.setAttribute(this.el.nativeElement, 'style', `opacity: 0; height: auto;`);

    switch (o.options.position) {
      case 'bottom':
        position.top = o.event.y + o.source.offsetHeight / 2;

        if (eRight > bodyWidth) {
          position.right = POSITION_MARGIN * 2;
        } else {
          position.left = o.event.x;
        }

        if (eBottom > bodyHeight) {
          position.height = bodyHeight - position.top - POSITION_MARGIN;
        }

        break;
    }

    this.renderer.setAttribute(el, 'style', `opacity: .9; ${this.getPositionString(position)}`);
  }

  getPositionString(po: any) {
    return Object.keys(po).reduce((p, c) => p + (po[c] ? `${c}: ${po[c]}px;` : ''), '');
  }

  buildComponent(o: TooltipOptions) {
    this.options = o;
    this.source = this.options.source;
    this.CurrentComponent = { issue: IssueInfoComponent, status: StatusInfoComponent }[this.options.options.componentName] || SimpleTextComponent;

    const emitter = new EventEmitter();
    emitter.pipe(take(1), delay(100), this.takeUntil()).subscribe(() => this.position());

    this.componentInjector = Injector.create({
      providers: [
        {
          provide: ComponentData,
          useValue: { typeName: this.router.url, current: this.options.options.content, emitter: emitter }
        }
      ],
      parent: this.parentInjector
    });
  }
}
