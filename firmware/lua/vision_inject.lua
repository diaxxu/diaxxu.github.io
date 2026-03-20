-- vision_inject.lua
-- Drop Pod — ArduPlane Lua Companion Script
-- =========================================
-- Runs on the F405/H743 FC alongside ArduPlane.
-- Receives visual correction data from the RPi companion
-- computer via MAVLink NAMED_VALUE_FLOAT messages and
-- injects them as attitude setpoint adjustments.
--
-- How to install:
--   1. Copy this file to the FC SD card: APM/scripts/vision_inject.lua
--   2. Set SCR_ENABLE = 1 in ArduPlane params
--   3. Reboot FC
--   4. Verify script is running: check GCS messages for "vision_inject: active"

-- ──────────────────────────────────────────────────────────────
-- CONFIGURATION
-- ──────────────────────────────────────────────────────────────

local MAX_CORRECTION_DEG = 15.0   -- Hard clamp on corrections
local CORRECTION_TIMEOUT_MS = 500  -- Zero out if no update for 500ms
local SCRIPT_RATE_HZ = 20         -- Script update rate

-- ──────────────────────────────────────────────────────────────
-- STATE
-- ──────────────────────────────────────────────────────────────

local roll_correction_deg  = 0.0
local pitch_correction_deg = 0.0
local last_update_ms       = 0
local active               = false

gcs:send_text(6, "vision_inject: active")

-- ──────────────────────────────────────────────────────────────
-- MAVLink MESSAGE HANDLER
-- Receives NAMED_VALUE_FLOAT messages from RPi Pi:
--   name = "VIS_ROLL" → roll correction in degrees
--   name = "VIS_PTCH" → pitch correction in degrees
-- ──────────────────────────────────────────────────────────────

local function handle_mavlink()
    -- ArduPlane Lua can listen to named value floats
    -- The Pi sends these via pymavlink named_value_float_send()
    -- This runs at the script update rate
    local msg = mavlink:recv_chan(mavlink.CHANNEL_0)
    if msg then
        if msg:get_type() == "NAMED_VALUE_FLOAT" then
            local name = msg:field("name")
            local val  = msg:field("value")

            if name == "VIS_ROLL" then
                roll_correction_deg  = math.max(-MAX_CORRECTION_DEG,
                                        math.min(MAX_CORRECTION_DEG, val))
                last_update_ms = millis()
                active = true

            elseif name == "VIS_PTCH" then
                pitch_correction_deg = math.max(-MAX_CORRECTION_DEG,
                                         math.min(MAX_CORRECTION_DEG, val))
                last_update_ms = millis()
                active = true
            end
        end
    end
end

-- ──────────────────────────────────────────────────────────────
-- WATCHDOG: zero corrections if no update received recently
-- ──────────────────────────────────────────────────────────────

local function check_timeout()
    if active and (millis() - last_update_ms) > CORRECTION_TIMEOUT_MS then
        roll_correction_deg  = 0.0
        pitch_correction_deg = 0.0
        active = false
        gcs:send_text(6, "vision_inject: timeout — corrections zeroed")
    end
end

-- ──────────────────────────────────────────────────────────────
-- MAIN UPDATE FUNCTION
-- ──────────────────────────────────────────────────────────────

local function update()
    handle_mavlink()
    check_timeout()

    -- Only inject corrections in AUTO or GUIDED mode
    local mode = vehicle:get_mode()
    if mode ~= 10 and mode ~= 4 then  -- 10=AUTO, 4=GUIDED
        return
    end

    if not active then
        return
    end

    -- Get current attitude target from ArduPlane
    local target_roll_cd  = vehicle:get_target_roll_cd()
    local target_pitch_cd = vehicle:get_target_pitch_cd()

    if target_roll_cd == nil or target_pitch_cd == nil then
        return
    end

    -- Apply corrections (convert degrees → centidegrees)
    local new_roll_cd  = target_roll_cd  + (roll_correction_deg  * 100)
    local new_pitch_cd = target_pitch_cd + (pitch_correction_deg * 100)

    -- Clamp to vehicle limits
    new_roll_cd  = math.max(-3500, math.min(3500, new_roll_cd))
    new_pitch_cd = math.max(-3000, math.min(2000, new_pitch_cd))

    -- Inject corrected target
    vehicle:set_target_roll_cd(new_roll_cd)
    vehicle:set_target_pitch_cd(new_pitch_cd)
end

-- ──────────────────────────────────────────────────────────────
-- SCRIPT REGISTRATION
-- ──────────────────────────────────────────────────────────────

return coroutine.create(function()
    while true do
        update()
        coroutine.yield(1000 / SCRIPT_RATE_HZ)  -- ms between calls
    end
end)
