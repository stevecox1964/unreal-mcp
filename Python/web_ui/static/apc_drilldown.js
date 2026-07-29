/* APC JSON drill-down (#43).
 *
 * Two layers, deliberately: dedicated components render the per-APC shapes we
 * know (authored agenda, execution task states, ledger, interruptions, survey
 * progress) as labeled summaries, and a generic recursive renderer handles
 * nested or unrecognized data underneath them.  Raw JSON stays available but
 * secondary — never the primary way to read an APC.
 *
 * Everything is written with textContent; APC files are user-authored and must
 * not be able to inject markup into the cockpit.
 *
 * TEST-FLAG (#43): expandable nesting keeps labels at every depth, task status
 * and completion evidence read without JSON syntax, depth/node caps truncate
 * instead of hanging on malformed or huge data, and an unreachable runner or a
 * non-object payload renders the bounded error state. Suggested level: offline
 * DOM/template coverage; no Unreal or model call required.
 */
(function (global) {
  'use strict';

  var MAX_DEPTH = 6;      // deeper than any real per-APC shape; stops cycles cheaply
  var MAX_ITEMS = 200;    // per collection, so one runaway array can't lock the page

  var STATUS_COLORS = {
    active: '#2d6a4f',
    completed: '#6c757d',
    pending: '#495057',
    interrupted: '#9c6f19',
    blocked: '#9b2226',
    waiting: '#495057',
    idle: '#6c757d'
  };

  function el(tag, text, css) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (css) node.style.cssText = css;
    return node;
  }

  function isPlain(value) {
    return value !== null && typeof value === 'object';
  }

  function describe(value) {
    if (Array.isArray(value)) return value.length + (value.length === 1 ? ' item' : ' items');
    if (isPlain(value)) {
      var keys = Object.keys(value);
      return keys.length + (keys.length === 1 ? ' field' : ' fields');
    }
    return '';
  }

  function humanize(key) {
    return String(key).replace(/_/g, ' ').replace(/^./, function (c) { return c.toUpperCase(); });
  }

  function scalarText(value) {
    if (value === null) return '—';
    if (value === '') return '(empty)';
    if (typeof value === 'boolean') return value ? 'yes' : 'no';
    return String(value);
  }

  /* Generic recursive renderer: objects/arrays become collapsible <details>
   * carrying their own label, scalars render as "Label: value" rows. */
  function renderValue(label, value, depth) {
    depth = depth || 0;
    if (!isPlain(value)) {
      var row = el('div', null, 'display:flex; gap:.5rem; padding:.1rem 0; font-size:.85rem');
      row.appendChild(el('span', humanize(label) + ':', 'color:#666; flex:0 0 auto'));
      row.appendChild(el('span', scalarText(value), 'font-family:monospace'));
      return row;
    }
    if (depth >= MAX_DEPTH) {
      return el('div', humanize(label) + ': … (nested too deep to expand here)',
                'font-size:.85rem; color:#888');
    }

    var details = el('details', null, 'margin:.15rem 0 .15rem ' + (depth ? '.9rem' : '0'));
    var summary = el('summary', null, 'cursor:pointer; font-size:.85rem');
    summary.appendChild(el('strong', humanize(label)));
    summary.appendChild(el('span', ' ' + describe(value), 'color:#888; font-weight:normal'));
    details.appendChild(summary);

    var body = el('div', null, 'border-left:2px solid #e5e5e5; margin-left:.4rem; padding-left:.6rem');
    var entries = Array.isArray(value)
      ? value.map(function (item, i) { return ['#' + (i + 1), item]; })
      : Object.keys(value).map(function (key) { return [key, value[key]]; });

    entries.slice(0, MAX_ITEMS).forEach(function (pair) {
      body.appendChild(renderValue(pair[0], pair[1], depth + 1));
    });
    if (entries.length > MAX_ITEMS) {
      body.appendChild(el('div', '… ' + (entries.length - MAX_ITEMS) + ' more not shown',
                          'font-size:.8rem; color:#888'));
    }
    details.appendChild(body);
    return details;
  }

  function statusPill(status) {
    var pill = el('span', status || 'unknown',
      'font-size:.75rem; padding:.1rem .5rem; border-radius:10px; color:#fff; background:'
      + (STATUS_COLORS[status] || '#6c757d'));
    return pill;
  }

  function card(title, note) {
    var box = el('article', null, 'margin:.6rem 0; padding:.7rem 1rem');
    var head = el('header', null, 'display:flex; justify-content:space-between; align-items:center; gap:.5rem; margin-bottom:.4rem; padding:0');
    head.appendChild(el('strong', title));
    if (note) head.appendChild(el('small', note, 'color:#888'));
    box.appendChild(head);
    return box;
  }

  function notice(text, tone) {
    return el('p', text, 'font-size:.85rem; color:' + (tone === 'error' ? '#9b2226' : '#888')
              + '; margin:.2rem 0');
  }

  /* ── Dedicated components ─────────────────────────────────────────────── */

  function rightNowCard(context, execution) {
    var right = (context && context.right_now) || null;
    var box = card('Right now', execution && execution.day ? execution.day : null);
    if (!right) {
      box.appendChild(notice('No agenda context available.'));
      return box;
    }
    var line = el('div', null, 'display:flex; align-items:center; gap:.5rem; flex-wrap:wrap');
    line.appendChild(statusPill(right.status));
    if (right.task_id) {
      line.appendChild(el('strong', right.objective || right.task_id));
      if (right.place) line.appendChild(el('span', 'at ' + right.place, 'color:#666'));
      line.appendChild(el('code', right.task_id, 'font-size:.75rem; color:#888'));
    } else {
      line.appendChild(el('span', right.status === 'waiting'
        ? 'Waiting for the next agenda task.'
        : 'No agenda task is active.', 'color:#666'));
    }
    box.appendChild(line);
    if (right.completion && right.completion.type) {
      box.appendChild(el('div', 'Completes on: ' + right.completion.type,
                         'font-size:.85rem; color:#666; margin-top:.3rem'));
    }
    if (right.active_interrupt) {
      var interrupt = card('Suspended by an interruption', null);
      interrupt.style.cssText += 'border-left:3px solid #9c6f19';
      interrupt.appendChild(renderValue('interrupt', right.active_interrupt, 0));
      box.appendChild(interrupt);
    }
    return box;
  }

  function nextCard(context) {
    var next = context && context.next;
    var box = card('Next', null);
    if (!next) {
      box.appendChild(notice('No unfinished agenda task remains.'));
      return box;
    }
    box.appendChild(el('div', next.objective + (next.place ? ' at ' + next.place : ''),
                       'font-weight:600'));
    box.appendChild(el('div', 'Activates at ' + next.activates_at + ' — '
                       + (next.activation_condition || ''),
                       'font-size:.85rem; color:#666'));
    return box;
  }

  function ledgerCard(context, execution) {
    var ledger = (context && context.today_so_far) || (execution && execution.ledger) || [];
    var box = card('Today so far', ledger.length + ' event' + (ledger.length === 1 ? '' : 's'));
    if (!ledger.length) {
      box.appendChild(notice('Nothing completed or blocked yet.'));
      return box;
    }
    ledger.slice(-MAX_ITEMS).forEach(function (entry) {
      if (!isPlain(entry)) return;
      var row = el('div', null, 'padding:.25rem 0; border-bottom:1px solid #f0f0f0');
      var head = el('div', null, 'display:flex; align-items:center; gap:.5rem; flex-wrap:wrap');
      head.appendChild(el('code', entry.world_time || '?', 'font-size:.75rem; color:#888'));
      head.appendChild(statusPill(entry.event));
      head.appendChild(el('span', entry.objective || entry.kind || entry.task_id || 'work'));
      row.appendChild(head);
      if (entry.evidence && isPlain(entry.evidence)) {
        row.appendChild(renderValue('evidence', entry.evidence, 1));
      }
      box.appendChild(row);
    });
    return box;
  }

  function tasksCard(authored, execution) {
    var tasks = (authored && authored.tasks) || [];
    var states = {};
    ((execution && execution.tasks) || []).forEach(function (state) {
      if (isPlain(state) && state.task_id) states[state.task_id] = state;
    });
    var box = card('Agenda tasks', authored ? 'authored — ' + tasks.length : 'no authored agenda');
    if (!tasks.length) {
      box.appendChild(notice('No authored agenda tasks.'));
      return box;
    }
    tasks.forEach(function (task) {
      if (!isPlain(task)) return;
      var state = states[task.id] || {};
      var row = el('div', null, 'padding:.3rem 0; border-bottom:1px solid #f0f0f0');
      var head = el('div', null, 'display:flex; align-items:center; gap:.5rem; flex-wrap:wrap');
      head.appendChild(el('code', (task.start || '?') + '–' + (task.end || '?'),
                          'font-size:.78rem; color:#666'));
      head.appendChild(statusPill(state.status || 'pending'));
      head.appendChild(el('span', task.objective || task.id, 'font-weight:600'));
      if (task.place) head.appendChild(el('span', 'at ' + task.place, 'color:#666'));
      row.appendChild(head);

      var detail = { authored: task };
      if (Object.keys(state).length) detail.runtime = state;
      row.appendChild(renderValue('details', detail, 1));
      box.appendChild(row);
    });
    return box;
  }

  function surveyCard(progress) {
    if (!isPlain(progress)) return null;
    var box = card('Survey in progress', progress.cell || null);
    var head = el('div', null, 'display:flex; align-items:center; gap:.5rem; flex-wrap:wrap');
    head.appendChild(statusPill(progress.phase));
    if (progress.current_heading) {
      head.appendChild(el('span', 'facing ' + progress.current_heading));
    }
    box.appendChild(head);
    box.appendChild(renderValue('progress', progress, 1));
    return box;
  }

  function rawCard(data) {
    var box = card('Raw JSON', 'advanced');
    var details = el('details');
    details.appendChild(el('summary', 'Show the unformatted inspect payload',
                           'cursor:pointer; font-size:.85rem'));
    var text;
    try {
      text = JSON.stringify(data, null, 2);
    } catch (err) {
      text = 'Payload could not be serialized for display.';
    }
    details.appendChild(el('pre', text,
      'background:#f4f4f4; padding:1rem; border-radius:4px; overflow-x:auto; font-size:.75rem; max-height:24rem'));
    box.appendChild(details);
    return box;
  }

  /* ── Entry point ──────────────────────────────────────────────────────── */

  function renderRuntime(container, data) {
    container.textContent = '';
    if (!isPlain(data)) {
      container.appendChild(notice('Live APC state is unavailable or malformed.', 'error'));
      return;
    }
    if (data.error || data.status === 'error') {
      container.appendChild(notice(String(data.error || 'Live APC state is unavailable.'), 'error'));
      return;
    }

    var errors = data.agenda_errors || [];
    if (errors.length) {
      var box = card('Agenda rejected by the runtime', null);
      box.style.cssText += 'border-left:3px solid #9b2226';
      errors.slice(0, MAX_ITEMS).forEach(function (message) {
        box.appendChild(notice(String(message), 'error'));
      });
      container.appendChild(box);
    }

    container.appendChild(rightNowCard(data.agenda_context, data.agenda_execution));
    container.appendChild(nextCard(data.agenda_context));
    container.appendChild(tasksCard(data.authored_agenda, data.agenda_execution));
    container.appendChild(ledgerCard(data.agenda_context, data.agenda_execution));

    var survey = surveyCard(data.survey_progress);
    if (survey) container.appendChild(survey);

    if (isPlain(data.state) || data.interrupt_queue) {
      var other = card('Other APC state', null);
      if (data.interrupt_queue) other.appendChild(renderValue('interrupt_queue', data.interrupt_queue, 0));
      if (data.last_interrupt) other.appendChild(renderValue('last_interrupt', data.last_interrupt, 0));
      if (isPlain(data.state)) other.appendChild(renderValue('state', data.state, 0));
      container.appendChild(other);
    }

    container.appendChild(rawCard(data));
  }

  global.apcDrilldown = {
    renderValue: renderValue,
    renderRuntime: renderRuntime
  };
})(window);
