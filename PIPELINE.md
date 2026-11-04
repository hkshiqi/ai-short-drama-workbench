# PIPELINE · 交接物 schema（六步版）

## 四层锁定

```
第一层 故事层   script.json                ← 第①步
第二层 视觉层   LOCK_V1 / SCN_LOCK_V1 / EXPR_LOCK_V1 / 音色表   ← 第②步
第三层 镜头层   BLOCK_*.csv（视觉列+音频列+时长列）              ← 第③④步
第四层 执行     视频候选 / 尾帧 / 验证报告 / 成片                ← 第⑤⑥步
```

**改上层才允许动下层。执行期（⑤⑥）不许改前三层。**

---

## script.json schema（第 ①步出口，②③④只读）

```json
{
  "project": "剧名",
  "version": "v1",
  "spec": {
    "eps": 12, "ep_sec": 90, "blocks_per_ep": 6,
    "block_sec": 15.0, "bpm": 128, "bar_sec": 1.875,
    "aspect": "9:16", "style": "真人写实电影感", "lang": "zh-CN", "platform": "douyin"
  },
  "characters": [
    {
      "id": "C_LEAD", "name": "林昭", "role": "主角",
      "surface": "外卖员", "true_id": "集团少东",
      "want": "母亲手术费", "obstacle": "继母设局", "weakness": "死要面子",
      "tag": "摸左手腕表",
      "outfits": ["OUTFIT_A", "OUTFIT_B", "OUTFIT_C"],
      "voice_id": "______",
      "face_photo": "path_or_null"
    }
  ],
  "scenes": [
    { "id": "SCN_CITY_ALLEY_NIGHT", "name": "城中村巷口·夜·雨",
      "lock": "SCN_LOCK_V1 内容", "light_ref": "场景图/SCN_CITY_ALLEY_NIGHT/LIGHT_REF.png" }
  ],
  "items": [
    { "id": "ITEM_WATCH", "name": "旧钢表", "type": "剧情道具",
      "views": ["正面", "侧面", "45°"], "hand_view": "PROD_HAND.png" }
  ],
  "products": [
    { "id": "P_MAIN", "brand": "BRAND_A", "sku": "SERUM-30",
      "claims": ["卖点1", "卖点2", "卖点3"], "claims_visual": ["画面化1", "画面化2", "画面化3"] }
  ],
  "episodes": [
    {
      "ep": 1, "title": "雨夜的订单", "sec": 92,
      "hard_hook": { "type": "危机降临", "line": "你送的不是外卖，是我儿子的命。" },
      "blocks": [
        {
          "block": 1, "bar_start": 1, "bar_len": 8, "sec": 15.0,
          "phase": "冷开场·压",
          "emotion_arc": "EXP_GRIEF_M → EXP_RESOLVE_M",
          "bgm_intent": { "layers": ["PAD"], "cue": "进", "ambience": "雨夜环境" },
          "sfx_points": ["雨声底噪"],
          "soft_hook": "「你送的不是外卖」",
          "scene": "SCN_CITY_ALLEY_NIGHT",
          "shots": [
            {
              "shot": 1, "bar_start": 1, "dur_bar": 2, "dur_sec": 3.75,
              "size": "ECU", "camera": "EYE", "move": "STATIC",
              "expr": "EXP_GRIEF_M", "expr_int": 1,
              "chars": ["C_LEAD"], "outfit": "OUTFIT_A",
              "frame_in": "B01_SH01_IN.png", "frame_out": "B01_SH01_OUT.png",
              "line": "—", "sub": "—",
              "product": null, "level": null, "model_tag": "FACE",
              "chain_break": false
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 块卡 CSV（第③④步产物，第⑤步唯一输入）

`04_场景分镜/BLOCK_EP{NN}_B{NN}.csv`

### 视觉列
| 列 | 必填 | 说明 |
|---|---|---|
| `ep` | ✓ | 集号 |
| `block` | ✓ | 块号 |
| `shot` | ✓ | 镜号（块内连号） |
| `frame_in` | ✓ | 首帧文件路径（真实存在） |
| `frame_out` | ✓ | 尾帧文件路径（真实存在） |
| `shot_size` | ✓ | ECU/CU/MS/MFS/FS/ELS |
| `camera` | ✓ | EYE/LOW/HIGH/OTS/PROFILE/BCK/POV/DUTCH |
| `move` | ✓ | STATIC/PUSH_S/PULL_S/PAN_S/TILT_S/TRACK_S/HANDHELD_L/RACK |
| `expr_code` | ✓ | EXP_{BASE}_{L/M/H} |
| `expr_int` | ✓ | 1/2/3 |
| `char_ids` | ✓ | 逗号分隔，≤2 |
| `outfit` | | OUTFIT_A/B/C |
| `product` | | 产品 ID 或"无" |
| `level` | | L1/L2/L3 或"无" |
| `model_tag` | ✓ | HERO/FACE/REACT/HAND/PROD/ENV/CROWD |
| `chain_break` | ✓ | true/false（本镜是否断链重开） |

### 音频列
| 列 | 必填 | 说明 |
|---|---|---|
| `line` | ✓ | 台词原文，"—"为无 |
| `sub_text` | ✓ | 字幕文本（显式写，不从台词抓） |
| `voice_emotion` | ✓ | 同 expr_code |
| `sfx` | ✓ | 音效名，"—"为无 |
| `bgm_layer` | ✓ | PAD/LOOP/STRINGS/HIT |
| `bgm_cue` | ✓ | 进/BEAT@n/BEAT_DROP@n/降/停 |
| `ambience` | ✓ | 环境声 |

### 时长列
| 列 | 必填 | 说明 |
|---|---|---|
| `bar_start` | ✓ | 本块内起始小节（1–8） |
| `bar_len` | ✓ | 本镜占小节数 |
| `dur_bar` | ✓ | = bar_len |
| `dur_sec` | ✓ | **= dur_bar × 1.875，不许手填** |

### 提示词列（第④步填）
| 列 | 必填 | 说明 |
|---|---|---|
| `first_frame_prompt` | ✓ | 可直接贴的完整首帧提示词 |
| `last_frame_prompt` | ✓ | 可直接贴的完整尾帧提示词 |
| `video_prompt` | ✓ | 图生视频运动描述 |
| `negative` | ✓ | 负向词 |

---

## 其他交接物

| 文件 | 版本 | 产出于 | 被谁读 |
|---|---|---|---|
| `02_角色/外观锁定词.md` | LOCK_V1 | ② | ③④ |
| `02_角色/表情片段库.md` | EXPR_LOCK_V1 | ② | ③④⑤ |
| `02_角色/音色表.md` | VOICE_V1 | ② | ⑤⑥ |
| `04_场景分镜/场景设定.md` | SCN_LOCK_V1 | ② | ③④ |
| `04_场景分镜/配乐卡点表_EP{NN}.csv` | v1 | ③ | ⑤⑥ |
| `04_场景分镜/抽卡台账.csv` | 追加 | ⑤ | 复盘 |
| `05_成片/验证报告_EP{NN}_B{NN}.md` | v1 | ⑤ | ⑥ |

---

## 状态记录

| 时间 | 步 | 产物 | 校验 | 决策点 |
|---|---|---|---|---|
| — | — | — | — | — |
