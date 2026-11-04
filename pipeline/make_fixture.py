# -*- coding: utf-8 -*-
"""make_fixture.py · 造一份完整仿真项目（用于全流程测试）

不是"假数据"——是一份结构完全合规、可用于跑通全流程的最小真实项目：
1 集 × 6 块 × 24 镜，含 3 角色 / 2 场景 / 2 物品 / 三份锁定词 / 音色表 / 服装表。

镜元组格式（15 元）：
  (景别, 机位, 运镜, 表情码, 强度, 角色[], 服装, 台词, 字幕, 音效, BGM层, BGM cue, 产品, 产品等级, 模型标签)
环境声由块级 ambience 统一注入。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import BAR_SEC, BLOCK_SEC, ROOT, Project, bars_to_sec, write_json

SLUG = "demo_雨夜的订单"

EXPR_LOCK = {
    "EXP_ANGER_L": "眉心微微下压，目光平直不移，嘴唇自然闭合并轻微收紧",
    "EXP_ANGER_M": "眉心明显下压形成竖纹，上眼睑抬高露出更多眼白，鼻翼微张，下颌绷紧，下唇前推",
    "EXP_ANGER_H": "眉低压近眼睛，眼球突出，鼻翼大幅扩张，嘴唇向后拉露出牙齿，颈部青筋",
    "EXP_GRIEF_L": "内眉头上抬，眼眶微微湿润，嘴角向下拉平",
    "EXP_GRIEF_M": "内眉头上抬成八字，下眼睑下方饱满有水光，鼻头微红，下唇微颤",
    "EXP_GRIEF_H": "眉心紧皱成川，双眼泛红含泪未落，面颊绷起，嘴唇抖开露出齿关",
    "EXP_SHOCK_L": "眉毛微抬，眼睛比平时略睁大，嘴唇轻启",
    "EXP_SHOCK_M": "双眉高抬，眼睛明显睁圆，瞳孔收缩，嘴唇张开成小圆形，下巴微坠",
    "EXP_SHOCK_H": "双眉极致上抬，眼白大量露出，嘴唇大张，面部肌肉停滞，颈部后仰",
    "EXP_CONTEMPT_L": "单侧嘴角极轻上扬，视线从下往上扫",
    "EXP_CONTEMPT_M": "单侧鼻翼上提，单侧嘴角拉高，眼睛半阖自上而下看人，下巴抬高",
    "EXP_CONTEMPT_H": "整张脸向上皱起，单侧露齿，眼皮半垂，鼻孔对人，头向后仰",
    "EXP_RESOLVE_L": "眼神稳定不眨，嘴唇轻合，下巴平正",
    "EXP_RESOLVE_M": "眼睛微眯，目光定点不移，下颌前送一点，脖颈拉直",
    "EXP_RESOLVE_H": "眼睑压低成一条缝但精光外露，眉平直，下颌紧咬，呼吸可见",
    "EXP_TENDER_L": "眼角柔和，嘴唇自然微弯，眼神放空",
    "EXP_TENDER_M": "下眼睑上推形成卧蚕，嘴角对称微上扬，眉放松",
    "EXP_TENDER_H": "眼睛弯成弧，笑意到眼底，脸颊上提，唇微启露齿",
}

LOCKS = {
    "C_LEAD": "28岁亚洲男性，窄长脸，颧骨清晰，内双细长眼，眉骨略高，薄唇，短寸黑发，"
              "肤色偏黄白，身高178体型偏瘦但肩宽，左手腕戴旧钢带手表，右眉尾有一道浅疤",
    "C_VILLAIN": "46岁亚洲女性，鹅蛋脸，颧骨高，上挑细长眼，眉形锋利，薄唇，"
                 "深棕色齐肩短卷发，肤色白皙，身高165体型清瘦，右耳戴一枚金色圆环耳饰",
    "C_ALLY": "25岁亚洲女性，小圆脸，眼大而圆，双眼皮，鼻头小巧，唇厚，"
              "黑色长直发及胸，肤色偏白，身高162体型纤细，颈间有细银链",
}

SCN_LOCK = {
    "SCN_ALLEY_NIGHT": "狭窄老旧巷子，两侧老式米白瓷砖墙与生锈空调外机，地面积水反光，"
                       "残缺品红霓虹招牌横挂在左上方，顶灯冷白从上方直下，右侧品红反光，"
                       "青蓝主调加品红点缀，夜雨，空气有雨雾",
    "SCN_ROOM_DUSK": "老式两居室客厅，米黄色墙面有水渍，木质旧家具，白炽灯偏暖，"
                     "窗外夕阳橙红从右侧斜射，桌上有搪瓷缸与旧报纸，暖黄主调，薄尘",
}

OUTFITS = {
    "OUTFIT_A": "深灰工装夹克，洗旧黑T恤，黑工装裤，旧帆布鞋",
    "OUTFIT_B": "黑色衬衫袖口卷两折，深灰西裤，黑色皮鞋",
    "OUTFIT_C": "灰色连帽卫衣，深蓝牛仔裤，白色球鞋",
    "OUTFIT_V": "深紫丝绒外套，黑色高领毛衣，黑色长裤",
    "OUTFIT_W": "米白针织开衫，浅灰长裙",
}

ITEMS = {
    "ITEM_WATCH": "旧钢带手表，表盘泛黄有划痕，表带为多节钢链，直径约36mm，银色",
    "P_MAIN": "透明磨砂玻璃瓶，圆柱瓶身，银色按压泵头，白色标签印黑字，容量30ml",
}

# (景别,机位,运镜,表情,强度,角色[],服装,台词,字幕,音效,BGM层,cue,产品,等级,tag)
BLOCKS = [
    dict(block=1, phase="冷开场·压", emotion_arc="EXP_GRIEF_M → EXP_RESOLVE_M",
         layers=["PAD"], cue="进", ambience="雨夜环境", sfx=["雨声底噪"],
         soft_hook="「最后一单。」", scene="SCN_ALLEY_NIGHT",
         shots=[
             ("ECU", "EYE", "STATIC", "EXP_GRIEF_M", 1, ["C_LEAD"], "OUTFIT_A", "—", "—", "雨声底噪", "PAD", "进", "无", "无", "FACE"),
             ("CU", "EYE", "PUSH_S", "EXP_GRIEF_M", 2, ["C_LEAD"], "OUTFIT_A", "最后一单。", "最后一单。", "雨声", "PAD", "进", "无", "无", "FACE"),
             ("MS", "LOW", "STATIC", "EXP_RESOLVE_M", 2, ["C_LEAD"], "OUTFIT_A", "—", "—", "雨声", "PAD", "进", "无", "无", "REACT"),
             ("CU", "OTS", "STATIC", "EXP_SHOCK_M", 2, ["C_LEAD"], "OUTFIT_A", "你找谁。", "你找谁。", "门开声", "PAD", "进", "无", "无", "FACE"),
         ]),
    dict(block=2, phase="铺垫·闷", emotion_arc="EXP_CONTEMPT_M → EXP_ANGER_L",
         layers=["PAD", "LOOP"], cue="LOOP_IN", ambience="楼道回声", sfx=["门铃"],
         soft_hook="「她认识这只表」", scene="SCN_ALLEY_NIGHT",
         shots=[
             ("CU", "PROFILE", "STATIC", "EXP_CONTEMPT_M", 2, ["C_VILLAIN"], "OUTFIT_V", "站着干什么。", "站着干什么。", "—", "LOOP", "LOOP_IN", "无", "无", "FACE"),
             ("ECU", "EYE", "STATIC", "EXP_ANGER_L", 1, ["C_LEAD"], "OUTFIT_A", "—", "—", "—", "LOOP", "进", "ITEM_WATCH", "无", "HAND"),
             ("MS", "OTS", "STATIC", "EXP_CONTEMPT_M", 2, ["C_VILLAIN", "C_LEAD"], "OUTFIT_V", "东西放下，走。", "东西放下，走。", "—", "LOOP", "进", "无", "无", "REACT"),
             ("CU", "EYE", "STATIC", "EXP_ANGER_L", 2, ["C_LEAD"], "OUTFIT_A", "—", "—", "—", "LOOP", "进", "ITEM_WATCH", "无", "HAND"),
         ]),
    dict(block=3, phase="加压·紧", emotion_arc="EXP_CONTEMPT_H → EXP_GRIEF_M",
         layers=["PAD", "LOOP", "STRINGS"], cue="BEAT@3", ambience="雨声渐大", sfx=["雷声"],
         soft_hook="「这表你哪来的」", scene="SCN_ROOM_DUSK",
         shots=[
             ("MS", "LOW", "STATIC", "EXP_CONTEMPT_H", 3, ["C_VILLAIN"], "OUTFIT_V", "这块表，早该熔了。", "这块表，早该熔了。", "雷声", "STRINGS", "BEAT@3", "无", "无", "HERO"),
             ("ECU", "EYE", "STATIC", "EXP_GRIEF_M", 2, ["C_LEAD"], "OUTFIT_A", "—", "—", "—", "STRINGS", "进", "ITEM_WATCH", "无", "HAND"),
             ("CU", "HIGH", "STATIC", "EXP_GRIEF_M", 2, ["C_LEAD"], "OUTFIT_A", "我妈的东西。", "我妈的东西。", "—", "STRINGS", "进", "无", "无", "FACE"),
             ("MS", "EYE", "STATIC", "EXP_CONTEMPT_M", 2, ["C_VILLAIN"], "OUTFIT_V", "你妈？", "你妈？", "—", "STRINGS", "进", "无", "无", "FACE"),
         ]),
    dict(block=4, phase="顶点前·憋", emotion_arc="EXP_GRIEF_H → EXP_ANGER_M",
         layers=["PAD", "LOOP"], cue="KICK_OUT", ambience="雨停", sfx=["心跳"],
         soft_hook="「你再说一遍」", scene="SCN_ROOM_DUSK",
         shots=[
             ("CU", "EYE", "STATIC", "EXP_GRIEF_H", 3, ["C_LEAD"], "OUTFIT_A", "—", "—", "心跳", "LOOP", "KICK_OUT", "无", "无", "FACE"),
             ("ECU", "EYE", "STATIC", "EXP_GRIEF_H", 3, ["C_LEAD"], "OUTFIT_A", "你再说一遍。", "你再说一遍。", "—", "LOOP", "进", "无", "无", "HERO"),
             ("MS", "OTS", "STATIC", "EXP_CONTEMPT_M", 2, ["C_VILLAIN"], "OUTFIT_V", "我说，你妈欠的，你还不清。", "我说，你妈欠的，你还不清。", "—", "LOOP", "进", "无", "无", "FACE"),
             ("ECU", "EYE", "STATIC", "EXP_ANGER_M", 2, ["C_LEAD"], "OUTFIT_A", "—", "—", "—", "LOOP", "进", "ITEM_WATCH", "无", "HAND"),
         ]),
    dict(block=5, phase="反转·爆", emotion_arc="EXP_RESOLVE_M → EXP_SHOCK_M",
         layers=["PAD", "LOOP", "STRINGS", "HIT"], cue="BEAT_DROP@1", ambience="寂静",
         sfx=["低频砸击"], soft_hook="「股东名册」", scene="SCN_ROOM_DUSK",
         shots=[
             ("CU", "EYE", "PUSH_S", "EXP_RESOLVE_M", 2, ["C_LEAD"], "OUTFIT_B", "欠的，我今天还。", "欠的，我今天还。", "低频砸击", "HIT", "BEAT_DROP@1", "无", "无", "HERO"),
             ("ECU", "EYE", "STATIC", "EXP_SHOCK_M", 2, ["C_VILLAIN"], "OUTFIT_V", "—", "—", "—", "STRINGS", "进", "无", "无", "FACE"),
             ("ECU", "EYE", "STATIC", "EXP_RESOLVE_M", 2, ["C_LEAD"], "OUTFIT_B", "—", "—", "纸质翻页", "STRINGS", "进", "P_MAIN", "L3", "PROD"),
             ("MS", "LOW", "STATIC", "EXP_RESOLVE_H", 3, ["C_LEAD"], "OUTFIT_B", "股东名册，第三页。", "股东名册，第三页。", "—", "STRINGS", "进", "无", "无", "HERO"),
         ]),
    dict(block=6, phase="断点·悬", emotion_arc="EXP_SHOCK_H → EXP_RESOLVE_M",
         layers=["PAD", "HIT"], cue="LOOP_OUT", ambience="雨声回归", sfx=["心跳", "whoosh"],
         soft_hook="断在此", scene="SCN_ROOM_DUSK",
         shots=[
             ("CU", "EYE", "STATIC", "EXP_SHOCK_H", 3, ["C_VILLAIN"], "OUTFIT_V", "不可能。", "不可能。", "心跳", "PAD", "LOOP_OUT", "无", "无", "FACE"),
             ("ECU", "EYE", "STATIC", "EXP_SHOCK_H", 3, ["C_VILLAIN"], "OUTFIT_V", "—", "—", "—", "PAD", "进", "无", "无", "HAND"),
             ("CU", "EYE", "PULL_S", "EXP_CONTEMPT_L", 1, ["C_LEAD"], "OUTFIT_B", "—", "—", "—", "PAD", "进", "无", "无", "HERO"),
             ("MS", "EYE", "STATIC", "EXP_RESOLVE_M", 2, ["C_LEAD"], "OUTFIT_B", "明天，你搬出去。", "明天，你搬出去。", "whoosh", "HIT", "HIT", "无", "无", "HERO"),
         ]),
]


def build_script():
    blocks_out = []
    for b in BLOCKS:
        shots = []
        for i, s in enumerate(b["shots"], start=1):
            (sz, cam, mv, expr, eint, chars, outfit,
             line, sub, sfx, layer, cue, prod, lvl, tag) = s
            shots.append({
                "shot": i, "bar_start": (i - 1) * 2 + 1, "dur_bar": 2,
                "dur_sec": bars_to_sec(2),
                "size": sz, "camera": cam, "move": mv,
                "expr": expr, "expr_int": eint,
                "chars": chars, "outfit": outfit,
                "line": line, "sub": sub, "sfx": sfx,
                "bgm_layer": layer, "bgm_cue": cue, "ambience": b["ambience"],
                "product": prod, "level": lvl, "model_tag": tag,
                # 断链：每块首镜断链；B03 第 4 镜再断一次（景别跳变）
                "chain_break": (i == 1 and b["block"] > 1) or (i == 4 and b["block"] == 3),
            })
        blocks_out.append({
            "block": b["block"], "bar_start": 1, "bar_len": 8, "sec": BLOCK_SEC,
            "phase": b["phase"], "emotion_arc": b["emotion_arc"],
            "bgm_intent": {"layers": b["layers"], "cue": b["cue"]},
            "sfx_points": b["sfx"],
            "soft_hook": b["soft_hook"], "scene": b["scene"],
            "shots": shots,
        })

    episodes = [{
        "ep": 1, "title": "雨夜的订单", "sec": BLOCK_SEC * 6,
        "hard_hook": {"type": "身份揭露", "line": "明天，你搬出去。"},
        "blocks": blocks_out,
    }]

    return {
        "project": "雨夜的订单",
        "slug": SLUG,
        "version": "v1",
        "spec": {"eps": 1, "ep_sec": int(round(BLOCK_SEC * 6)), "blocks_per_ep": 6,
                 "block_sec": BLOCK_SEC, "bpm": 128, "bar_sec": BAR_SEC,
                 "aspect": "9:16", "lang": "zh-CN", "platform": "douyin",
                 # 第①步必选：风格锁定
                 "style": {
                     "style_id": "CINEMA_REAL",
                     "overlays": ["FILM_GRAIN", "NEON_LIGHT"],
                     "topic": "复仇爽剧",
                     "note": "冷雨夜都市复仇，电影感写实 + 胶片颗粒 + 霓虹多色",
                 }},
        "characters": [
            {"id": "C_LEAD", "name": "林昭", "role": "主角",
             "surface": "外卖员", "true_id": "集团少东",
             "want": "拿回母亲的手术费与遗物", "obstacle": "继母设局夺产",
             "weakness": "死要面子", "tag": "摸左手腕表",
             "outfits": ["OUTFIT_A", "OUTFIT_B", "OUTFIT_C"],
             "voice_id": "VOICE_LEAD_01", "face_photo": None},
            {"id": "C_VILLAIN", "name": "顾曼", "role": "反派",
             "surface": "顾氏集团代董事长", "true_id": "继母",
             "want": "吞掉全部股份", "obstacle": "名义上的继承人",
             "weakness": "怕被揭老底", "tag": "抬下巴看人",
             "outfits": ["OUTFIT_V"], "voice_id": "VOICE_VILLAIN_01", "face_photo": None},
            {"id": "C_ALLY", "name": "苏念", "role": "女主",
             "surface": "律所助理", "true_id": "—",
             "want": "帮林昭翻案", "obstacle": "她自己的债务",
             "weakness": "太容易心软", "tag": "说话时低头看手",
             "outfits": ["OUTFIT_W"], "voice_id": "VOICE_ALLY_01", "face_photo": None},
        ],
        "scenes": [
            {"id": "SCN_ALLEY_NIGHT", "name": "城中村巷口·夜·雨",
             "lock": SCN_LOCK["SCN_ALLEY_NIGHT"]},
            {"id": "SCN_ROOM_DUSK", "name": "老式两居室客厅·夜",
             "lock": SCN_LOCK["SCN_ROOM_DUSK"]},
        ],
        "items": [
            {"id": "ITEM_WATCH", "name": "旧钢表", "type": "剧情道具",
             "desc": ITEMS["ITEM_WATCH"]},
            {"id": "P_MAIN", "name": "清透精华水", "type": "产品",
             "desc": ITEMS["P_MAIN"], "brand": "BRAND_A", "sku": "SERUM-30",
             "claims": ["质地细腻", "清爽不闷", "便携可单手取用"],
             "claims_visual": ["手背推开有柔光反光", "上脸后擦毛巾不黏", "从通勤小包单手取出"]},
        ],
        "episodes": episodes,
    }


def main():
    proj = Project(ROOT, SLUG)
    proj.ensure_dirs()

    script = build_script()
    write_json(proj.d_script / "script.json", script)

    lock_md = "# 外观锁定词 · LOCK_V1\n\n"
    for cid, txt in LOCKS.items():
        lock_md += f"## {cid}\n\n**中文**\n\n{txt}\n\n**EN**\n\n(en version)\n\n"
    (proj.d_char / "外观锁定词.md").write_text(lock_md, encoding="utf-8")

    expr_md = "# 表情片段库 · EXPR_LOCK_V1\n\n| code | 中文描述 |\n|---|---|\n"
    for k, v in EXPR_LOCK.items():
        expr_md += f"| {k} | {v} |\n"
    (proj.d_char / "表情片段库.md").write_text(expr_md, encoding="utf-8")

    scn_md = "# 场景设定 · SCN_LOCK_V1\n\n"
    for sid, txt in SCN_LOCK.items():
        scn_md += f"## {sid}\n\n**中文**\n\n{txt}\n\n**EN**\n\n(en version)\n\n"
    (proj.d_scene / "场景设定.md").write_text(scn_md, encoding="utf-8")

    outfit_md = "# 服装表\n\n| code | 描述 |\n|---|---|\n"
    for k, v in OUTFITS.items():
        outfit_md += f"| {k} | {v} |\n"
    (proj.d_char / "服装表.md").write_text(outfit_md, encoding="utf-8")

    voice_md = ("# 音色表 · VOICE_V1\n\n"
                "| 角色 | 音高 | 语速 | 质感 | 音色ID | 试听 | 通过 |\n|---|---|---|---|---|---|---|\n"
                "| C_LEAD | 偏低 | 0.95x | 微哑克制 | VOICE_LEAD_01 | lead.mp3 | Y |\n"
                "| C_VILLAIN | 中高 | 1.05x | 尖、齿音重 | VOICE_VILLAIN_01 | villain.mp3 | Y |\n"
                "| C_ALLY | 中 | 1.00x | 清亮 | VOICE_ALLY_01 | ally.mp3 | Y |\n")
    (proj.d_char / "音色表.md").write_text(voice_md, encoding="utf-8")

    n_shot = sum(len(b["shots"]) for e in script["episodes"] for b in e["blocks"])
    print(f"fixture 已生成: {proj.d_script / 'script.json'}")
    print(f"  角色 {len(script['characters'])} | 场景 {len(script['scenes'])} | "
          f"物品 {len(script['items'])} | 集 {len(script['episodes'])} | "
          f"块 {sum(len(e['blocks']) for e in script['episodes'])} | 镜 {n_shot}")


if __name__ == "__main__":
    main()
