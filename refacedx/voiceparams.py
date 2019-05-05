import string

part_mode = (
    "Poly",
    "Mono-Full",
    "Mono-Legato",
)
lfo_wave = (
    "Sine",
    "Triangle",
    "Sawtooth up",
    "Sawtooth down",
    "Square",
    "Sample & Hold 8",
    "Sample & Hold",
)
effect_type = (
    "Thru",
    "Distortion",
    "Touch Wah",
    "Chorus",
    "Flanger",
    "Phaser",
    "Delay",
    "Reverb",
)
ksc_level_curve = (
    ("-LIN", "-Linear"),
    ("-EXP", "-Exponential"),
    ("+EXP", "+Exponential"),
    ("+LIN", "+Linear"),
)

# offset, size, type, name, range, mapping, description
params_common = (
    (0x00, 10, str, "voice_name", (32, 126), string.printable[:-6], "Voice Name"),
    (0x0a, 2, None, "reserved", None, None, None),
    (0x0c, 1, int, "transpose", 0x28-0x58, (-24, 24), "Transposition (semitones)"),
    (0x0d, 1, int, "part_mode", (0, 2), part_mode, "Part (Voice) Mode"),
    (0x0e, 1, int, "portamento_time", (0, 127), None, "Portamento time"),
    (0x0f, 1, int, "pb_range", (0x28, 0x58), (-24, 24), "Pitch bend range"),
    (0x10, 1, int, "algorithm", (0, 11), None, "Algorithm 1-12"),
    (0x11, 1, int, "lfo_wave", (0, 6), lfo_wave, "LFO Waveform"),
    (0x12, 1, int, "lfo_speed", (0, 127), None, "LFO Speed"),
    (0x13, 1, int, "lfo_delay", (0, 127), None, "LFO Delay"),
    (0x14, 1, int, "lfp_pmd", (0, 127), None, "LFO Pitch Modulation Depth"),
    (0x15, 1, int, "pitch_eg_rate_1", (0, 127), None, "Pitch EG Rate 1"),
    (0x16, 1, int, "pitch_eg_rate_2", (0, 127), None, "Pitch EG Rate 2"),
    (0x17, 1, int, "pitch_eg_rate_3", (0, 127), None, "Pitch EG Rate 3"),
    (0x18, 1, int, "pitch_eg_rate_4", (0, 127), None, "Pitch EG Rate 4"),
    (0x19, 1, int, "pitch_eg_level_1", (0, 127), None, "Pitch EG Level 1"),
    (0x1a, 1, int, "pitch_eg_level_2", (0, 127), None, "Pitch EG Level 2"),
    (0x1b, 1, int, "pitch_eg_level_3", (0, 127), None, "Pitch EG Level 3"),
    (0x1c, 1, int, "pitch_eg_level_4", (0, 127), None, "Pitch EG Level 4"),
    (0x1d, 1, int, "effect_1_type", (0, 7), effect_type, "Effect 1 Type"),
    (0x1e, 1, int, "effect_1_param1", (0, 127), None, "Effect 1 Parameter 1"),
    (0x1f, 1, int, "effect_1_param2", (0, 127), None, "Effect 1 Parameter 2"),
    (0x20, 1, int, "effect_2_type", (0, 7), effect_type, "Effect 2 Type"),
    (0x21, 1, int, "effect_2_param1", (0, 127), None, "Effect 2 Parameter 1"),
    (0x22, 1, int, "effect_2_param2", (0, 127), None, "Effect 2 Parameter 2"),
    (0x23, 3, None, "reserved", None, None, None)
)

params_op = (
    (0x00, 1, bool, "op_enable", (0, 1), None,"Operator On/Off"),
    (0x01, 1, int, "op_eg_rate_1", (0, 127), None, "Operator EG Rate 1"),
    (0x02, 1, int, "op_eg_rate_2", (0, 127), None, "Operator EG Rate 2"),
    (0x03, 1, int, "op_eg_rate_3", (0, 127), None, "Operator EG Rate 3"),
    (0x04, 1, int, "op_eg_rate_4", (0, 127), None, "Operator EG Rate 4"),
    (0x05, 1, int, "op_eg_level_1", (0, 127), None, "Operator EG Level 1"),
    (0x06, 1, int, "op_eg_level_2", (0, 127), None, "Operator EG Level 2"),
    (0x07, 1, int, "op_eg_level_3", (0, 127), None, "Operator EG Level 3"),
    (0x08, 1, int, "op_eg_level_4", (0, 127), None, "Operator EG Level 4"),
    (0x09, 1, int, "op_eg_ksc_rate", (0, 127), None, "Operator EG Keyboard Rate Scaling"),
    (0x0a, 1, int, "op_eg_ksc_level_depth_l", (0, 127), None, "Operator EG Keyboard Level Scaling Depth Left"),
    (0x0b, 1, int, "op_eg_ksc_level_depth_r", (0, 127), None, "Operator EG Keyboard Level Scaling Depth Right"),
    (0x0c, 1, int, "op_eg_ksc_level_curve_l", (0, 3), ksc_level_curve, "Operator EG Keyboard Level Scaling Curve Left"),
    (0x0d, 1, int, "op_eg_ksc_level_curve_r", (0, 3), ksc_level_curve, "Operator EG Keyboard Level Scaling Curve Right"),
    (0x0e, 1, int, "op_lfo_amd", (0, 127), None, "LFO Operator Amplitude Modulation Depth"),
    (0x0f, 1, bool, "op_lfo_pm_enable", (0, 1), None, "LFO Operator Pitch Modulation On/Off"),
    (0x10, 1, bool, "op_peg_pm_enable", (0, 1), None, "Pitch EG Operator Pitch Modulation On/Off"),
    (0x11, 1, int, "op_leveL_velocity_sens", (0, 127), None, "Operator Level Velocity Sensitivity"),
    (0x12, 1, int, "op_leveL", (0, 127), None, "Operator Output Level"),
    (0x13, 1, int, "op_feedback_level", (0, 127), None, "Operator Feedback Level"),
    (0x14, 1, int, "op_feedback_type", (0, 1), ("sawtooth", "square"), "Operator Feedback Type"),
    (0x15, 1, int, "op_freq_mode", (0, 1), ("ration", "fixed"), "Operator Frequency Mode"),
    (0x16, 1, int, "op_freq_ratio_coarse", (0, 0x1f), None, "Operator Frequency Ratio Coarse"),
    (0x17, 1, int, "op_freq_ratio_fine", (0, 63), None, "Operator Frequency Ratio Fine"),
    (0x18, 1, int, "op_freq_detunes", (0, 127), (-64, 63), "Operator Frequency Detune"),
    (0x19, 3, None, "reserved", None, None, None)
)
