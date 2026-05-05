from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import pytz
import openai
import json
import re
import config
from database import db
from mcp_server import mcp_server

app = Flask(__name__)
CORS(app)

openai.api_key = config.OPENAI_API_KEY

# ─── TIMEZONE ────────────────────────────────────────────────────────────────
KUWAIT_TZ = pytz.timezone('Asia/Kuwait')   # UTC+3, no DST

def now_kuwait():
    """Return the current datetime in Kuwait time (timezone-aware)."""
    return datetime.now(KUWAIT_TZ)

def today_kuwait():
    """Return today's date in Kuwait time."""
    return now_kuwait().date()

# ─── IN-MEMORY STATE ─────────────────────────────────────────────────────────
chat_history = []
pending_optimization_plan = None   # Stores the latest optimization plan waiting for approval

# Each entry: {'id': str, 'device': str, 'action': str, 'value': any,
#              'scheduled_time': datetime (Kuwait-aware), 'timer': threading.Timer,
#              'revert_action': str, 'revert_value': any, 'revert_timer': threading.Timer or None}
scheduled_actions = []
scheduled_actions_lock = threading.Lock()

with open('agent_prompt_compact.md', 'r') as f:
    SYSTEM_PROMPT = f.read()


# ─── SCHEDULER HELPERS ───────────────────────────────────────────────────────

def _parse_scheduled_time(time_str):
    """
    Parse the start_time field from the optimization plan into a
    Kuwait-timezone-aware datetime.

    Accepts:
      - ISO8601 with date  e.g. '2025-04-21T16:00:00'
      - Time only          e.g. '16:00' or '16:00:00'
        (treated as today's date in Kuwait time)

    Returns a timezone-aware datetime (Asia/Kuwait), or None on failure.
    """
    if not time_str or time_str == 'N/A':
        return None

    today = today_kuwait()

    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%H:%M:%S', '%H:%M'):
        try:
            dt = datetime.strptime(time_str, fmt)
            if fmt in ('%H:%M:%S', '%H:%M'):
                # Time-only: attach today's Kuwait date
                dt = dt.replace(year=today.year, month=today.month, day=today.day)
            # Localise to Kuwait (the parsed time IS Kuwait time)
            return KUWAIT_TZ.localize(dt)
        except ValueError:
            continue
    return None


def _get_revert_action(device, action, value):
    """
    Determine what the revert action should be when the scheduled window ends.
    - turn_off  → revert to turn_on
    - turn_on   → revert to turn_off
    - set_intensity → revert to turn_on (restore normal operation)
    Returns (revert_action, revert_value).
    """
    if action == 'turn_off':
        return 'turn_on', 'N/A'
    elif action == 'turn_on':
        return 'turn_off', 'N/A'
    elif action == 'set_intensity':
        # Restore to full intensity (100%) when the window ends
        return 'set_intensity', '100'
    return None, None


def _execute_scheduled_action(device, action, value, action_id):
    """
    Called by threading.Timer when a scheduled action fires.
    Executes the MCP command and removes the action from the in-memory list.
    """
    try:
        kw_time = now_kuwait().strftime("%I:%M %p")
        print(f"[SCHEDULER] {kw_time} — Executing: {device} → {action} (id={action_id})")
        if action == 'turn_on':
            mcp_server.turn_on_device({"device": device})
        elif action == 'turn_off':
            mcp_server.turn_off_device({"device": device})
        elif action == 'set_intensity':
            intensity = int(value) if value not in (None, 'N/A') else 0
            mcp_server.set_motor_intensity({"percent_0_to_100": intensity})
        print(f"[SCHEDULER] Done: {device} → {action}")
    except Exception as e:
        print(f"[SCHEDULER] Failed: {device} → {action}: {e}")
    finally:
        with scheduled_actions_lock:
            global scheduled_actions
            scheduled_actions = [a for a in scheduled_actions if a['id'] != action_id]


def _execute_revert_action(device, revert_action, revert_value, action_id):
    """
    Called by threading.Timer when the end_time of a scheduled window arrives.
    Reverts the device back to its pre-action state.
    """
    try:
        kw_time = now_kuwait().strftime("%I:%M %p")
        print(f"[SCHEDULER] {kw_time} — Reverting: {device} → {revert_action} (id={action_id}_revert)")
        if revert_action == 'turn_on':
            mcp_server.turn_on_device({"device": device})
        elif revert_action == 'turn_off':
            mcp_server.turn_off_device({"device": device})
        elif revert_action == 'set_intensity':
            intensity = int(revert_value) if revert_value not in (None, 'N/A') else 100
            mcp_server.set_motor_intensity({"percent_0_to_100": intensity})
        print(f"[SCHEDULER] Revert done: {device} → {revert_action}")
    except Exception as e:
        print(f"[SCHEDULER] Revert failed: {device} → {revert_action}: {e}")


def _schedule_plan(schedule):
    """
    Given a proposed_schedule list from the optimization plan,
    create a threading.Timer for each action at its start_time (Kuwait time).
    Also creates a revert timer at end_time so the device returns to its
    previous state after the scheduled window closes.
    Cancels any previously pending timers first.
    Returns a human-readable summary list.
    """
    summary = []
    now_kw  = now_kuwait()

    with scheduled_actions_lock:
        # Cancel any previously scheduled actions and their revert timers
        for entry in scheduled_actions:
            entry['timer'].cancel()
            if entry.get('revert_timer'):
                entry['revert_timer'].cancel()
        scheduled_actions.clear()

        for idx, item in enumerate(schedule):
            device    = item.get('device', 'Unknown')
            action    = item.get('action', 'N/A')
            value     = item.get('value', 'N/A')
            start_str = item.get('start_time', 'N/A')
            end_str   = item.get('end_time', 'N/A')

            scheduled_dt = _parse_scheduled_time(start_str)
            end_dt       = _parse_scheduled_time(end_str)

            if scheduled_dt is None:
                summary.append(f"  {device} ({action}): could not parse time '{start_str}' — skipped")
                continue

            delay_seconds = (scheduled_dt - now_kw).total_seconds()

            if delay_seconds < 0:
                delay_seconds = 0
                time_note = "immediately (scheduled time already passed)"
            else:
                time_note = scheduled_dt.strftime("%I:%M %p")

            action_id = f"action_{idx}_{int(now_kw.timestamp())}"

            # ── Main action timer ──────────────────────────────────────────────
            timer = threading.Timer(
                delay_seconds,
                _execute_scheduled_action,
                args=[device, action, value, action_id]
            )
            timer.daemon = True
            timer.start()

            # ── Revert timer (fires at end_time) ───────────────────────────────
            revert_timer = None
            revert_action, revert_value = _get_revert_action(device, action, value)

            if end_dt is not None and revert_action is not None:
                revert_delay = (end_dt - now_kw).total_seconds()
                if revert_delay > 0:
                    revert_timer = threading.Timer(
                        revert_delay,
                        _execute_revert_action,
                        args=[device, revert_action, revert_value, action_id]
                    )
                    revert_timer.daemon = True
                    revert_timer.start()

            scheduled_actions.append({
                'id':             action_id,
                'device':         device,
                'action':         action,
                'value':          value,
                'scheduled_time': scheduled_dt,
                'timer':          timer,
                'revert_action':  revert_action,
                'revert_value':   revert_value,
                'revert_timer':   revert_timer
            })

            if action == 'set_intensity':
                action_text = f"Set intensity to {value}%"
            elif action == 'turn_off':
                action_text = "Turn OFF"
            elif action == 'turn_on':
                action_text = "Turn ON"
            else:
                action_text = action

            summary.append(f"  {device} → {action_text} at {time_note}")

    return summary


def _format_plan_response(agent_data):
    """
    Formats the optimization plan JSON into a human-readable chat message.
    Returns the formatted string.
    """
    def format_time(iso_timestamp):
        """Convert an ISO timestamp string to Kuwait-time 12-hour display."""
        if iso_timestamp == 'N/A':
            return 'N/A'
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            # If naive, treat as Kuwait time
            if dt.tzinfo is None:
                dt = KUWAIT_TZ.localize(dt)
            else:
                dt = dt.astimezone(KUWAIT_TZ)
            return dt.strftime("%I:%M %p").lstrip('0')
        except Exception:
            return iso_timestamp

    plan_data       = agent_data.get('optimization_plan', {}).get('plan', {})
    device_analysis = agent_data.get('device_status_analysis', {})
    budget_info     = agent_data.get('budget_comparison', {})

    out  = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    out += "       ENERGY OPTIMIZATION PLAN\n"
    out += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    out += "📊 CURRENT STATUS\n"
    total_wh  = budget_info.get('total_consumption_Wh', 'N/A')
    budget_wh = budget_info.get('budget_Wh', 'N/A')
    if total_wh != 'N/A' and budget_wh != 'N/A':
        total_kwh  = float(total_wh)  / 1000
        budget_kwh = float(budget_wh) / 1000
        out += f"   • Total Consumption: {total_kwh:.2f} kWh\n"
        out += f"   • Energy Budget:     {budget_kwh:.2f} kWh\n"
        out += f"   • Status:            {budget_info.get('result', 'N/A')}\n\n"

    out += "⚡ ACTIVE DEVICES\n"
    for device_name, info in device_analysis.items():
        status    = info.get('status', 'N/A')
        power     = info.get('power_W', 'N/A')
        energy_wh = info.get('energy_Wh', 'N/A')
        intensity = info.get('intensity_percent', 'N/A')

        status_icon = "🟢" if status == "ON" else "🔴"
        out += f"   {status_icon} {device_name}: {status}"
        if intensity != 'N/A':
            out += f" at {intensity}%"
        if power != 'N/A':
            out += f" ({power}W)"
        if energy_wh != 'N/A':
            out += f" | Today: {float(energy_wh)/1000:.2f} kWh"
        out += "\n"

    out += "\n📅 PROPOSED SCHEDULE\n"
    schedule = plan_data.get('proposed_schedule', [])
    for i, item in enumerate(schedule, 1):
        device     = item.get('device', 'N/A')
        action     = item.get('action', 'N/A')
        value      = item.get('value', 'N/A')
        start_time = item.get('start_time', 'N/A')
        end_time   = item.get('end_time', 'N/A')
        rationale  = item.get('rationale', 'N/A')

        if action == 'set_intensity':
            action_text = f"Set intensity to {value}%"
        elif action == 'turn_off':
            action_text = "Turn OFF"
        elif action == 'turn_on':
            action_text = "Turn ON"
        else:
            action_text = action

        out += f"\n   {i}. {device}\n"
        out += f"      → {action_text}\n"
        out += f"      ⏰ {format_time(start_time)} to {format_time(end_time)}\n"
        out += f"      💡 {rationale}\n"

    expected_impact = plan_data.get('expected_impact', 'N/A')
    if expected_impact != 'N/A':
        out += f"\n💰 EXPECTED SAVINGS\n   {expected_impact}\n"

    out += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    out += (
        "\n📌 HOW WOULD YOU LIKE TO APPLY THIS PLAN?\n\n"
        "   • Type  apply now  to execute all actions immediately.\n"
        "   • Type  apply  to schedule each action at its planned time\n"
        "     (one-time execution for today).\n"
        "   • Type  modify  followed by your changes to customise the plan\n"
        "     before applying it.  For example:\n"
        "       modify: change Motor to turn off at 15:30pm. Delete action 1. Delete action 2.\n"
    )

    return out


def _apply_modifications_to_plan(agent_data, modification_text):
    """
    Applies the user's free-text modification request to the current plan.

    Two strategies:
    1. DELETE ACTION N  — handled locally without GPT-4 by removing the
       item at the requested 1-based index from proposed_schedule.
    2. Everything else  — sent to GPT-4 which returns the updated full JSON.

    Always operates on and returns the FULL outer agent_data object so that
    device_status_analysis and budget_comparison are preserved for re-display.
    """
    today_str = today_kuwait().strftime('%Y-%m-%d')

    # ── Step 1: Handle "delete action N" locally (no GPT-4 needed) ──────────
    # Extract all "delete action N" instructions from the modification text.
    delete_pattern = re.compile(r'delete\s+action\s+(\d+)', re.IGNORECASE)
    delete_indices = [int(m.group(1)) for m in delete_pattern.finditer(modification_text)]

    # Remove delete instructions from the text so the remainder goes to GPT-4
    remaining_text = delete_pattern.sub('', modification_text).strip().strip('.,;').strip()

    # Apply deletions to the proposed_schedule (1-based indices, delete largest first)
    if delete_indices:
        schedule = agent_data.get('optimization_plan', agent_data).get('plan', {}).get('proposed_schedule', [])
        # Convert to 0-based and sort descending so removing by index is safe
        zero_based = sorted([i - 1 for i in delete_indices if 1 <= i <= len(schedule)], reverse=True)
        for idx in zero_based:
            del schedule[idx]
        # Write back
        if 'optimization_plan' in agent_data:
            agent_data['optimization_plan']['plan']['proposed_schedule'] = schedule
        else:
            agent_data.get('plan', {})['proposed_schedule'] = schedule

    # If there are no remaining text modifications, return the locally-edited plan
    if not remaining_text:
        return agent_data

    # ── Step 2: Send remaining modifications to GPT-4 ───────────────────────
    current_plan_json = json.dumps(agent_data, indent=2)

    modify_prompt = f"""
You are an Energy Management AI assistant.

The user has an existing energy optimization plan (shown below as JSON) and wants to modify some of its actions.

CURRENT PLAN:
{current_plan_json}

USER'S MODIFICATION REQUEST:
"{remaining_text}"

The user may want to modify one or multiple devices in a single request. For example:
- Change a device's action (e.g., turn off instead of set intensity)
- Change the motor intensity value (e.g., "set Motor to 60% instead of 40%")
- Change the scheduled time of one or more actions (e.g., "move Motor turn-off to 15:30")
- Modify multiple devices at once (e.g., "change Motor to turn off at 15:30 and set Fan intensity to 40%")
- Any combination of the above

INSTRUCTIONS:
1. Apply ALL the changes the user explicitly requested. Do NOT change anything else.
2. Return the COMPLETE updated plan JSON in the exact same structure as the input.
3. The proposed_schedule items must keep all fields: device, action, value, start_time, end_time, rationale.
4. All times are Kuwait time (UTC+3). If the user changes a time, update start_time (and end_time if relevant)
   in ISO8601 format using today's date: {today_str}.
5. If the user changes an action to turn_on or turn_off, set value to "N/A".
6. If the user changes intensity, set action to "set_intensity" and value to the new percentage as a string (e.g., "60").
7. Return ONLY valid JSON. No explanation, no markdown fences.
"""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an Energy Management AI assistant that modifies optimization plans in JSON format."},
            {"role": "user",   "content": modify_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    updated_json_str = response.choices[0].message.content.strip()
    if updated_json_str.startswith("```json"):
        updated_json_str = updated_json_str.replace("```json", "").replace("```", "").strip()
    elif updated_json_str.startswith("```"):
        updated_json_str = updated_json_str.replace("```", "").strip()

    return json.loads(updated_json_str)


# ─── FLASK ROUTES ─────────────────────────────────────────────────────────────

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    try:
        devices = db.get_all_devices()
        system_config = db.get_system_config()

        if not system_config:
            return jsonify({"error": "System configuration not found"}), 500

        total_consumption_wh   = system_config['total_consumption']
        energy_budget_kwh      = system_config['energy_budget']
        energy_budget_wh       = energy_budget_kwh * 1000
        remaining_budget_wh    = energy_budget_wh - total_consumption_wh
        efficiency_score       = (remaining_budget_wh / energy_budget_wh * 100) if energy_budget_wh > 0 else 0
        efficiency_score       = max(0, efficiency_score)
        consumption_percentage = (total_consumption_wh / energy_budget_wh * 100) if energy_budget_wh > 0 else 0
        consumption_status     = "Normal" if total_consumption_wh <= energy_budget_wh else "High"

        return jsonify({
            "devices":               [dict(d) for d in devices],
            "systemConfig":          dict(system_config),
            "remainingBudget":       remaining_budget_wh,
            "consumptionStatus":     consumption_status,
            "efficiencyScore":       efficiency_score,
            "consumptionPercentage": consumption_percentage
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/energy-budget', methods=['POST'])
def update_budget():
    try:
        data   = request.json
        budget = data.get('budget')

        if budget is None or budget < 0:
            return jsonify({"error": "Invalid budget value"}), 400

        db.update_energy_budget(budget)
        return jsonify({"success": True, "message": "Energy budget updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    try:
        device_id = request.args.get('device_id', type=int)
        readings  = db.get_recent_readings(device_id, hours=24)
        chart_data = []

        if device_id:
            for reading in readings:
                chart_data.append({
                    "time":  reading['reading_time'].isoformat(),
                    "value": reading['power'] / 1000
                })
        else:
            for reading in readings:
                chart_data.append({
                    "time":  reading['reading_time'].isoformat(),
                    "value": reading.get('total_power', 0) / 1000
                })

        return jsonify(chart_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scheduled-actions', methods=['GET'])
def get_scheduled_actions():
    """Returns the list of currently pending scheduled actions (Kuwait time)."""
    with scheduled_actions_lock:
        result = [
            {
                'id':             a['id'],
                'device':         a['device'],
                'action':         a['action'],
                'value':          a['value'],
                'scheduled_time': a['scheduled_time'].strftime("%Y-%m-%dT%H:%M:%S%z")
            }
            for a in scheduled_actions
        ]
    return jsonify({"scheduledActions": result})


@app.route('/api/chat', methods=['POST'])
def chat():
    global chat_history
    global pending_optimization_plan

    try:
        data         = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        chat_history.append({
            "role":      "user",
            "content":   user_message,
            "timestamp": now_kuwait().isoformat()
        })

        # ─── DETECT USER INTENT ──────────────────────────────────────────────
        msg_lower = user_message.lower().strip()

        # "apply now" — execute all actions immediately
        apply_now_keywords = ['apply now', 'execute now', 'run now', 'do it now', 'start now']
        is_apply_now = any(kw in msg_lower for kw in apply_now_keywords)

        # "modify" — user wants to customise the plan before applying
        is_modify = msg_lower.startswith('modify') and not is_apply_now

        # "apply" (scheduled) — schedule actions at their planned Kuwait times
        apply_scheduled_keywords = ['apply', 'approve', 'execute', 'yes', 'confirm', 'proceed', 'go ahead']
        is_apply_scheduled = (
            not is_apply_now and
            not is_modify and
            any(kw in msg_lower for kw in apply_scheduled_keywords)
        )

        # ─── PATH A: APPLY NOW ────────────────────────────────────────────────
        if is_apply_now and pending_optimization_plan:
            try:
                executed_actions = []
                plan_data = pending_optimization_plan.get('optimization_plan', pending_optimization_plan).get('plan', {})
                schedule  = plan_data.get('proposed_schedule', [])

                for item in schedule:
                    device = item.get('device')
                    action = item.get('action')
                    value  = item.get('value', 'N/A')

                    if action == 'turn_on':
                        mcp_server.turn_on_device({"device": device})
                        executed_actions.append(f"🟢 {device} turned ON")
                    elif action == 'turn_off':
                        mcp_server.turn_off_device({"device": device})
                        executed_actions.append(f"🔴 {device} turned OFF")
                    elif action == 'set_intensity':
                        intensity = int(value) if value not in (None, 'N/A') else 0
                        mcp_server.set_motor_intensity({"percent_0_to_100": intensity})
                        executed_actions.append(f"⚙️  Motor intensity set to {intensity}%")

                kw_time = now_kuwait().strftime("%I:%M %p")
                final_response  = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                final_response += "       PLAN EXECUTED IMMEDIATELY\n"
                final_response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                final_response += f"✅ All actions applied at {kw_time}:\n\n"
                final_response += "\n".join([f"   {a}" for a in executed_actions])
                final_response += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

                pending_optimization_plan = None

            except Exception as e:
                final_response = f"Failed to execute optimization plan: {str(e)}"

            chat_history.append({
                "role":      "assistant",
                "content":   final_response,
                "timestamp": now_kuwait().isoformat()
            })
            return jsonify({"response": final_response})

        # ─── PATH B: APPLY SCHEDULED ──────────────────────────────────────────
        if is_apply_scheduled and pending_optimization_plan:
            try:
                plan_data = pending_optimization_plan.get('optimization_plan', pending_optimization_plan).get('plan', {})
                schedule  = plan_data.get('proposed_schedule', [])

                schedule_summary = _schedule_plan(schedule)

                final_response  = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                final_response += "       PLAN SCHEDULED SUCCESSFULLY\n"
                final_response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                final_response += "⏰ The following actions will execute automatically\n"
                final_response += "   at their planned times:\n\n"
                final_response += "\n".join([f"{s}" for s in schedule_summary])
                final_response += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

                pending_optimization_plan = None

            except Exception as e:
                final_response = f"Failed to schedule optimization plan: {str(e)}"

            chat_history.append({
                "role":      "assistant",
                "content":   final_response,
                "timestamp": now_kuwait().isoformat()
            })
            return jsonify({"response": final_response})

        # ─── PATH C: MODIFY PLAN ──────────────────────────────────────────────
        if is_modify and pending_optimization_plan:
            try:
                # Strip the leading "modify" keyword and optional colon/space
                modification_text = re.sub(r'^modify[\s:,]*', '', user_message, flags=re.IGNORECASE).strip()

                if not modification_text:
                    final_response = (
                        "Please describe what you would like to change. For example:\n\n"
                        "   modify: change Motor to turn off at 15:30pm. Delete action 1. Delete action 2."
                    )
                    chat_history.append({
                        "role":      "assistant",
                        "content":   final_response,
                        "timestamp": now_kuwait().isoformat()
                    })
                    return jsonify({"response": final_response})

                # Use GPT-4 to apply the modifications to the current plan
                updated_agent_data = _apply_modifications_to_plan(
                    pending_optimization_plan,
                    modification_text
                )

                # Update the stored pending plan with the modified version
                pending_optimization_plan = updated_agent_data

                # Re-format and present the updated plan with all three options again
                final_response = _format_plan_response(updated_agent_data)

            except json.JSONDecodeError:
                final_response = "I was unable to parse the modified plan. Please try again with a clearer description of your changes."
            except Exception as e:
                final_response = f"Failed to modify the plan: {str(e)}"

            chat_history.append({
                "role":      "assistant",
                "content":   final_response,
                "timestamp": now_kuwait().isoformat()
            })
            return jsonify({"response": final_response})

        # ─── NORMAL AGENT FLOW ────────────────────────────────────────────────
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1200
            )

            agent_response = response.choices[0].message.content.strip()

            if agent_response.startswith("```json"):
                agent_response = agent_response.replace("```json", "").replace("```", "").strip()
            elif agent_response.startswith("```"):
                agent_response = agent_response.replace("```", "").strip()

            try:
                agent_data = json.loads(agent_response)

                print(f"\n{'='*60}")
                print(f"DEBUG - Agent Response Analysis")
                print(f"{'='*60}")
                print(f"Mode: {agent_data.get('mode', 'NOT FOUND')}")
                print(f"Summary: {agent_data.get('summary', 'NOT FOUND')}")
                print(f"MCP Data Requests: {len(agent_data.get('mcp_data_requests', []))}")
                print(f"Should Execute: {agent_data.get('direct_command', {}).get('should_execute', 'NOT FOUND')}")
                print(f"Needs Approval: {agent_data.get('optimization_plan', {}).get('needs_approval', 'NOT FOUND')}")
                if agent_data.get('mode') == 'OPTIMIZATION_PLAN':
                    plan_data  = agent_data.get('optimization_plan', {}).get('plan', {})
                    schedule   = plan_data.get('proposed_schedule', [])
                    print(f"Proposed Schedule Items: {len(schedule)}")
                    for i, item in enumerate(schedule, 1):
                        print(f"  {i}. {item.get('device')} - {item.get('action')}")
                print(f"{'='*60}\n")

            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                final_response = agent_response
                chat_history.append({
                    "role":      "assistant",
                    "content":   final_response,
                    "timestamp": now_kuwait().isoformat()
                })
                return jsonify({"response": final_response})

            # Execute MCP data requests
            mcp_results = []
            if agent_data.get('mcp_data_requests'):
                for request_item in agent_data['mcp_data_requests']:
                    tool_name = request_item.get('tool')
                    if tool_name == 'db_read':
                        query_type = request_item.get('query_type')
                        parameters = request_item.get('parameters', {})
                        result = mcp_server.call_tool('db_read', {'query_type': query_type, **parameters})
                        mcp_results.append({
                            'tool':       'db_read',
                            'query_type': query_type,
                            'parameters': parameters,
                            'result':     result
                        })
                    elif tool_name == 'read_system_status':
                        result = mcp_server.call_tool('read_system_status', {})
                        mcp_results.append({
                            'tool':   'read_system_status',
                            'result': result
                        })

            # Execute direct commands
            executed_commands = []
            if agent_data.get('direct_command', {}).get('should_execute') == 'true':
                commands = agent_data['direct_command'].get('commands', [])
                for cmd in commands:
                    tool   = cmd.get('tool')
                    device = cmd.get('device')
                    value  = cmd.get('value')

                    if tool == 'turn_on':
                        result = mcp_server.turn_on_device({"device": device})
                        executed_commands.append({'device': device, 'action': 'turn_on', 'result': result})
                    elif tool == 'turn_off':
                        result = mcp_server.turn_off_device({"device": device})
                        executed_commands.append({'device': device, 'action': 'turn_off', 'result': result})
                    elif tool == 'set_motor_intensity':
                        intensity = int(value) if value not in (None, 'N/A') else 0
                        result = mcp_server.set_motor_intensity({"percent_0_to_100": intensity})
                        executed_commands.append({'device': device, 'action': 'set_motor_intensity', 'intensity': intensity, 'result': result})

            # ── Branch routing ────────────────────────────────────────────────
            agent_mode     = agent_data.get('mode', '')
            needs_approval = agent_data.get('optimization_plan', {}).get('needs_approval', 'false')

            # ─── BRANCH 1: OPTIMIZATION PLAN ─────────────────────────────────
            if agent_mode == 'OPTIMIZATION_PLAN' and needs_approval == 'true' and mcp_results:
                follow_up_message = f"""
You requested the following data to create an optimization plan. Here are the results:

{json.dumps(mcp_results, indent=2, default=str)}

Now complete your OPTIMIZATION_PLAN JSON response with the actual data. Fill in the device_status_analysis and budget_comparison with real values from the results above, and create a detailed proposed_schedule array with specific optimization actions.

IMPORTANT: All times in the proposed_schedule must be in Kuwait time (UTC+3, Asia/Kuwait timezone).
Use ISO8601 format with today's date: {today_kuwait().strftime('%Y-%m-%d')}T<HH:MM:SS>

CRITICAL: Return ONLY valid JSON in the EXACT same format as your previous response, but now with:
1. device_status_analysis filled with actual device data from the MCP results (status, power_W, energy_Wh, intensity_percent)
2. budget_comparison filled with ACTUAL values:
   - total_consumption_Wh: read from "current_total_consumption" MCP result
   - budget_Wh: read from "budget" MCP result (look for "energy_budget_wh" field)
   - result: calculate if consumption exceeds budget
3. proposed_schedule array with 3-4 specific schedule items (device, action, value, start_time, end_time, rationale)
   All times are Kuwait time.
4. expected_impact with calculated energy savings based on actual device consumption

User's original request: "{user_message}"

Return the complete OPTIMIZATION_PLAN JSON now.
"""
                completion2 = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system",    "content": SYSTEM_PROMPT},
                        {"role": "user",      "content": user_message},
                        {"role": "assistant", "content": agent_response},
                        {"role": "user",      "content": follow_up_message}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )

                completed_response = completion2.choices[0].message.content.strip()
                if completed_response.startswith("```json"):
                    completed_response = completed_response.replace("```json", "").replace("```", "").strip()
                elif completed_response.startswith("```"):
                    completed_response = completed_response.replace("```", "").strip()

                try:
                    agent_data = json.loads(completed_response)

                    print(f"\n{'='*60}")
                    print(f"DEBUG - Completed Optimization Plan")
                    print(f"{'='*60}")
                    plan_data_check = agent_data.get('optimization_plan', {}).get('plan', {})
                    schedule_check  = plan_data_check.get('proposed_schedule', [])
                    print(f"Completed Schedule Items: {len(schedule_check)}")
                    for i, item in enumerate(schedule_check, 1):
                        print(f"  {i}. {item.get('device')} - {item.get('action')} @ {item.get('start_time')}")
                    print(f"{'='*60}\n")

                except json.JSONDecodeError as e:
                    print(f"Failed to parse completed optimization plan: {e}")
                    final_response = "Failed to generate optimization plan. Please try again."
                    chat_history.append({
                        "role":      "assistant",
                        "content":   final_response,
                        "timestamp": now_kuwait().isoformat()
                    })
                    return jsonify({"response": final_response})

                # Store the FULL agent_data so modify can access device_status_analysis
                # and budget_comparison when re-formatting the plan after changes
                pending_optimization_plan = agent_data
                final_response = _format_plan_response(agent_data)

            # ─── BRANCH 2: ENERGY REPORT ──────────────────────────────────────
            elif agent_mode == 'ENERGY_REPORT':
                report_devices = mcp_server.call_tool('db_read', {'query_type': 'latest_device_status'})
                report_total   = mcp_server.call_tool('db_read', {'query_type': 'current_total_consumption'})
                report_budget  = mcp_server.call_tool('db_read', {'query_type': 'budget'})

                total_wh        = report_total.get('total_consumption_wh', 0)
                total_kwh       = total_wh / 1000
                budget_kwh      = report_budget.get('energy_budget_kwh', 0)
                budget_wh       = budget_kwh * 1000
                remaining_wh    = budget_wh - total_wh
                remaining_kwh   = remaining_wh / 1000
                utilization_pct = (total_wh / budget_wh * 100) if budget_wh > 0 else 0
                budget_status   = 'Within Budget' if total_wh <= budget_wh else 'Budget Exceeded'

                devices = report_devices.get('devices', [])

                final_response  = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                final_response += "           ENERGY REPORT\n"
                final_response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                final_response += "📊 1. SYSTEM OVERVIEW\n"
                final_response += f"   • Total Energy Consumed : {total_kwh:.3f} kWh  ({total_wh:.1f} Wh)\n"
                final_response += f"   • Energy Budget         : {budget_kwh:.3f} kWh  ({budget_wh:.1f} Wh)\n"
                final_response += f"   • Remaining Budget      : {remaining_kwh:.3f} kWh  ({remaining_wh:.1f} Wh)\n"
                final_response += f"   • Budget Utilization    : {utilization_pct:.1f}%\n\n"

                final_response += "⚡ 2. DEVICE-BY-DEVICE BREAKDOWN\n"
                device_name_map = {1: 'Fan', 2: 'Motor', 3: 'Light Bulb'}
                for device in devices:
                    d_id        = device.get('id', device.get('device_id'))
                    d_name      = device.get('device_name', device_name_map.get(d_id, f'Device {d_id}'))
                    d_status    = device.get('device_status', 'N/A')
                    d_wh        = float(device.get('device_total_consumption', 0))
                    d_kwh       = d_wh / 1000
                    d_pct       = (d_wh / total_wh * 100) if total_wh > 0 else 0
                    d_intensity = device.get('device_intensity', None)

                    status_icon = '🟢' if d_status == 'ON' else '🔴'
                    final_response += f"\n   {status_icon} {d_name}\n"
                    final_response += f"      Status         : {d_status}\n"
                    final_response += f"      Total Consumed : {d_kwh:.3f} kWh  ({d_wh:.1f} Wh)\n"
                    final_response += f"      Share of Total : {d_pct:.1f}%\n"
                    if d_name == 'Motor' and d_intensity is not None:
                        final_response += f"      Intensity      : {d_intensity}%\n"

                final_response += "\n📋 3. BUDGET STATUS\n"
                if budget_status == 'Within Budget':
                    final_response += f"   ✅ Status: {budget_status}\n"
                    final_response += f"   The system has used {utilization_pct:.1f}% of its energy budget.\n"
                    final_response += f"   There is {remaining_kwh:.3f} kWh remaining before the budget is reached.\n"
                else:
                    over_kwh = abs(remaining_kwh)
                    final_response += f"   ⚠️  Status: {budget_status}\n"
                    final_response += f"   The system has exceeded its energy budget by {over_kwh:.3f} kWh.\n"

                final_response += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # ─── BRANCH 3: QUERY / OTHER MODES WITH DATA ──────────────────────
            elif mcp_results:
                follow_up_message = f"""
You requested the following data, here are the results:

{json.dumps(mcp_results, indent=2, default=str)}

Based on this data, provide your final answer to the user's question: "{user_message}"

Provide a clear, conversational response in plain English. Do not return JSON.

IMPORTANT RULES:
- This is an INDUSTRIAL IoT SYSTEM. Always refer to it as "system" or "energy management system", never as "home".
- If device consumption data is successfully retrieved, present it clearly.
"""
                completion2 = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system",    "content": "You are an Energy Management AI Assistant for an Industrial IoT System. Provide clear, conversational responses based on data. Always respond in natural language, never in JSON format."},
                        {"role": "user",      "content": user_message},
                        {"role": "assistant", "content": agent_response},
                        {"role": "user",      "content": follow_up_message}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                final_response = completion2.choices[0].message.content.strip()

            # ─── BRANCH 4: DIRECT COMMANDS EXECUTED ───────────────────────────
            elif executed_commands:
                if len(executed_commands) == 1:
                    cmd = executed_commands[0]
                    if cmd['action'] == 'turn_on':
                        final_response = f"{cmd['device']} has been turned ON successfully."
                    elif cmd['action'] == 'turn_off':
                        final_response = f"{cmd['device']} has been turned OFF successfully."
                    elif cmd['action'] == 'set_motor_intensity':
                        final_response = f"Motor intensity has been set to {cmd['intensity']}% successfully."
                    else:
                        final_response = f"Command executed successfully for {cmd['device']}."
                else:
                    device_names   = [cmd['device'] for cmd in executed_commands]
                    final_response = f"Successfully executed {len(executed_commands)} commands: {', '.join(device_names)}."

            # ─── BRANCH 5: NO MCP CALLS, NO COMMANDS ──────────────────────────
            else:
                final_response = agent_data.get('answer', agent_response)

            chat_history.append({
                "role":      "assistant",
                "content":   final_response,
                "timestamp": now_kuwait().isoformat()
            })
            return jsonify({"response": final_response})

        except Exception as openai_error:
            error_message = f"OpenAI API Error: {str(openai_error)}"
            print(f"Error: {error_message}")
            import traceback
            traceback.print_exc()
            chat_history.append({
                "role":      "assistant",
                "content":   error_message,
                "timestamp": now_kuwait().isoformat()
            })
            return jsonify({"response": error_message})

    except Exception as e:
        error_message = f"Server Error: {str(e)}"
        print(f"Error: {error_message}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_message}), 500


@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    return jsonify(chat_history)


@app.route('/api/optimization-plan', methods=['GET'])
def get_optimization_plan():
    if pending_optimization_plan:
        return jsonify({"optimizationPlan": pending_optimization_plan})
    else:
        return jsonify({"optimizationPlan": "No optimization plan available."})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
