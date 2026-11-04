# -*- coding: utf-8 -*-
"""stylelib.py · 风格库（31 主风格 + 3 类修饰层）

每条风格内置：
  id / name / group / tier / use_for / prompt_cn / prompt_en / negative / risk
第①步选风格 → 写进 script.json 的 spec.style → 第③④步自动拼进 first_frame_prompt。
"""
from __future__ import annotations

# ============================================================
# 主风格（6 组 31 种）
# ============================================================
STYLES: dict[str, dict] = {
    # ---------- A 电影写实系 ----------
    "CINEMA_REAL": dict(
        name="电影感写实", group="A电影写实", tier="S",
        use_for="任何题材，默认",
        prompt_cn="电影感画面，35mm 胶片质感，浅景深，电影级布光，高细节皮肤纹理，自然光影过渡，柔和对比，真实材质反射",
        prompt_en="cinematic film look, 35mm film texture, shallow depth of field, film-grade lighting, detailed skin texture, natural light falloff, soft contrast, realistic material reflections",
        negative="塑料感, 过锐, HDR 过曝, 动漫风, 3D 渲染, 插画感",
        risk=2),
    "CINEMA_COLD": dict(
        name="冷调电影感", group="A电影写实", tier="A",
        use_for="复仇、商战、悬疑前段",
        prompt_cn="冷调电影画面，青蓝色调，低饱和度，硬朗光影，高对比暗部，阴天散射光，金属与玻璃冷反射，压抑氛围",
        prompt_en="cold-tone cinematic look, cyan-blue grade, desaturated, hard directional light, deep high-contrast shadows, overcast diffused light, cold metal and glass reflections, oppressive mood",
        negative="暖黄, 橘调, 甜美, 高饱和",
        risk=2),
    "CINEMA_WARM": dict(
        name="暖调电影感", group="A电影写实", tier="A",
        use_for="家庭、回忆、团圆",
        prompt_cn="暖调电影画面，琥珀金色调，柔和暖光，窗光斜射，尘埃可见，皮肤有温度感，暗部保留细节，怀旧质感",
        prompt_en="warm-tone cinematic look, amber gold grade, soft warm lighting, angled window light, visible dust motes, warm skin tones, detailed shadows, nostalgic texture",
        negative="冷蓝, 青绿, 冷硬",
        risk=2),
    "TEAL_ORANGE": dict(
        name="青橙商业片", group="A电影写实", tier="A",
        use_for="产品广告、爽剧高光镜、投流素材",
        prompt_cn="青橙对比色调，人物暖橙色皮肤与冷青色环境分离，商业大片质感，清晰锐利，高动态范围，干净背景",
        prompt_en="teal and orange color grade, warm orange skin tones against cool teal environment, blockbuster commercial look, crisp and sharp, high dynamic range, clean background",
        negative="灰蒙, 低对比, 脏色",
        risk=2),
    "ANAMORPHIC": dict(
        name="变形宽银幕", group="A电影写实", tier="B",
        use_for="男主登场、品牌大片、集末钩（一集 2–3 镜）",
        prompt_cn="变形宽银幕镜头质感，横向蓝色拉丝光斑，椭圆散景，宽画幅电影感，轻微边缘柔化，镜头光晕",
        prompt_en="anamorphic lens look, horizontal blue lens flare streaks, oval bokeh, widescreen cinematic feel, slight edge softness, lens ghosting",
        negative="手机拍摄感, 平光, 无光斑",
        risk=3),
    "FILM_NOIR": dict(
        name="黑色电影", group="A电影写实", tier="B",
        use_for="悬疑、黑帮、审判戏",
        prompt_cn="黑色电影风格，硬质侧光，大面积深阴影，明暗对比强烈，百叶窗光条投影，烟雾弥漫，高反差带冷色倾向",
        prompt_en="film noir style, hard side light, large deep shadows, strong chiaroscuro, venetian blind light bars, drifting smoke, high-contrast with cool tint",
        negative="平光, 明亮, 甜美",
        risk=3),
    "DOC_REAL": dict(
        name="纪实写实", group="A电影写实", tier="S",
        use_for="婆媳家庭、社会议题、真实改编",
        prompt_cn="纪实风格画面，自然光，无人工布光痕迹，真实生活质感，轻微噪点，手持轻微晃动感，不过度美化皮肤",
        prompt_en="documentary style, natural available light, no artificial lighting, real-life texture, slight grain, subtle handheld feel, unretouched skin",
        negative="电影感过强, 完美皮肤, 影棚光",
        risk=2),
    "MACRO_TEXTURE": dict(
        name="微距质感", group="A电影写实", tier="A",
        use_for="产品特写、情绪大特写",
        prompt_cn="微距镜头质感，极浅景深，皮肤毛孔与细小绒毛可见，材质表面细节极致，柔和的环形光，背景完全虚化",
        prompt_en="macro lens look, extremely shallow depth of field, visible skin pores and fine vellus hair, extreme surface detail, soft ring light, completely blurred background",
        negative="磨皮, 塑料, 模糊",
        risk=3),

    # ---------- B 怀旧复古系 ----------
    "RETRO_90S_CN": dict(
        name="90年代国产怀旧", group="B怀旧复古", tier="A",
        use_for="重生回 90 年代、年代家庭剧",
        prompt_cn="90 年代中国怀旧画面，褪色暖黄色调，轻微偏色，柔和低对比，老式室内白炽灯光，颗粒感，年代感家居陈设",
        prompt_en="1990s Chinese nostalgic look, faded warm yellow grade, slight color cast, soft low contrast, old incandescent indoor light, visible grain, period-accurate home decor",
        negative="现代感, LED 冷光, 高清锐利",
        risk=3),
    "RETRO_HK": dict(
        name="港风复古", group="B怀旧复古", tier="A",
        use_for="港风爱情、都市怀旧、情绪戏",
        prompt_cn="港风复古电影感，浓郁饱和色块，深绿与酒红，霓虹招牌光，慢门拖影，烟雾感，潮湿街道反光，暧昧氛围",
        prompt_en="retro Hong Kong cinema look, rich saturated color blocks, deep green and burgundy, neon sign glow, slow-shutter motion trails, hazy atmosphere, wet reflective streets, moody vibe",
        negative="清淡, 冷调, 现代简约",
        risk=3),
    "VHS": dict(
        name="录像带质感", group="B怀旧复古", tier="C",
        use_for="伪纪录片、恐怖、回忆闪回（只做单镜）",
        prompt_cn="VHS 录像带质感，扫描线，色彩溢出与色差，磁带噪点，轻微画面抖动，底部时间戳水印，低分辨率柔化",
        prompt_en="VHS tape look, scanlines, chroma bleed and color fringing, tape noise, slight picture jitter, bottom timestamp overlay, softened low resolution",
        negative="高清, 4K, 干净, 锐利",
        risk=4),
    "FILM_16MM": dict(
        name="16mm胶片", group="B怀旧复古", tier="C",
        use_for="独立电影感、青春、公路",
        prompt_cn="16mm 胶片质感，明显颗粒，轻微画面划痕与灰尘，片门轻微抖动，自然柔和的宽容度，复古胶片色彩",
        prompt_en="16mm film look, prominent grain, occasional scratches and dust, slight gate weave, natural soft latitude, vintage film color",
        negative="数码感, 无颗粒, 极致锐利",
        risk=3),
    "POLAROID": dict(
        name="宝丽来照片感", group="B怀旧复古", tier="C",
        use_for="回忆闪回、定帧、片尾彩蛋（注意与 9:16 冲突）",
        prompt_cn="宝丽来即时照片质感，方形构图，白边框，正面闪光灯直打，偏色与褪色，柔和低对比，边缘轻微虚化",
        prompt_en="Polaroid instant photo look, square framing, white border, direct on-camera flash, color shift and fading, soft low contrast, slight edge blur",
        negative="宽画幅, 电影光, 高清",
        risk=3),
    "RETRO_80S": dict(
        name="80年代霓虹复古", group="B怀旧复古", tier="B",
        use_for="穿越、复古科幻、音乐段落",
        prompt_cn="80 年代复古未来主义，品红与青色霓虹，合成器浪潮配色，辉光溢出，网格线背景，蒸汽感",
        prompt_en="80s retro-futurism, magenta and cyan neon, synthwave palette, bloom glow overflow, grid line background, hazy vapor",
        negative="自然光, 低饱和, 现代",
        risk=3),
    "OLD_TV": dict(
        name="老电视机", group="B怀旧复古", tier="C",
        use_for="年代回忆、新闻报道、恐怖",
        prompt_cn="老式 CRT 电视机画面质感，圆角屏幕边缘，屏幕色边与暗角，扫描线与轻微雪花噪点，4:3 画幅感，模拟信号柔化",
        prompt_en="old CRT television look, rounded screen edges, chromatic fringing and vignette, scanlines and slight static noise, 4:3 framing feel, analog signal softness",
        negative="现代屏幕, 高清, 无噪点",
        risk=3),

    # ---------- C 类型片系 ----------
    "SUSPENSE_DARK": dict(
        name="悬疑暗调", group="C类型片", tier="B",
        use_for="悬疑反转、惊悚",
        prompt_cn="悬疑暗调画面，低调布光，仅局部被照亮，大量未知暗区，冷白单光源，长阴影，空气中浮尘，压抑不安氛围",
        prompt_en="suspense dark look, low-key lighting, only partial areas lit, large unknown shadow zones, single cold white source, long shadows, floating dust, oppressive unsettling mood",
        negative="明亮, 均匀布光, 阳光",
        risk=3),
    "ACTION_GRAIN": dict(
        name="动作粗粝", group="C类型片", tier="B",
        use_for="打斗、追车、复仇动作段（运镜必须 STATIC）",
        prompt_cn="动作片粗粝质感，高对比硬光，明显颗粒，脏污与磨损细节，手持感，冷硬色调，汗与尘可见",
        prompt_en="gritty action look, high-contrast hard light, prominent grain, grime and wear detail, handheld feel, cold hard grade, visible sweat and dust",
        negative="干净, 柔光, 唯美",
        risk=4),
    "ROMANCE_SOFT": dict(
        name="偶像剧柔光", group="C类型片", tier="S",
        use_for="都市甜宠、校园恋爱",
        prompt_cn="偶像剧柔光画面，柔焦镜效果，高调明亮布光，皮肤通透明亮，空气中有柔光晕，浅粉与米白色调，梦幻唯美",
        prompt_en="romantic soft-focus look, diffused filter effect, high-key bright lighting, luminous clear skin, soft glow halo in air, pale pink and cream tones, dreamy and beautiful",
        negative="硬光, 冷调, 粗颗粒, 脏",
        risk=2),
    "WAR_DESAT": dict(
        name="战争褪色", group="C类型片", tier="B",
        use_for="战争、年代苦难、末世",
        prompt_cn="战争片褪色质感，接近黑白的低饱和，土黄与灰绿，硝烟与尘土，粗颗粒，硬光高反差，画面有脏污与磨损",
        prompt_en="war film desaturated look, near-monochrome low saturation, ochre and gray-green, smoke and dust, coarse grain, hard high-contrast light, grimy worn texture",
        negative="鲜艳, 甜美, 干净",
        risk=3),
    "SCIFI_NEON": dict(
        name="科幻霓虹", group="C类型片", tier="B",
        use_for="未来、赛博、科技产品（屏幕文字单独出图）",
        prompt_cn="科幻画面质感，清冷蓝青主光，全息界面微光，体积光与雾，金属与玻璃高科技材质，未来感简洁线条",
        prompt_en="sci-fi look, cool blue-cyan key light, faint holographic UI glow, volumetric light and fog, high-tech metal and glass materials, futuristic clean lines",
        negative="复古, 木质, 暖黄",
        risk=3),
    "FANTASY_EPIC": dict(
        name="奇幻史诗", group="C类型片", tier="B",
        use_for="玄幻、仙侠、史诗开场（远景只做空镜）",
        prompt_cn="奇幻史诗画面，宏大尺度，大气透视，体积神光穿云，丰富层次的山川与建筑，史诗级布光，细节繁复",
        prompt_en="epic fantasy look, grand scale, atmospheric perspective, volumetric god rays through clouds, layered mountains and architecture, epic lighting, intricate detail",
        negative="日常, 平光, 小空间",
        risk=4),
    "ANCIENT_CN": dict(
        name="古装国风", group="C类型片", tier="A",
        use_for="古风宅斗、宫廷、武侠",
        prompt_cn="中式古装画面，绢本绘画质感，柔和暖调，烛火与窗棂光影，丝绸与木质材质细节，含蓄留白，古典雅致",
        prompt_en="Chinese period drama look, silk-scroll texture, soft warm grade, candlelight through lattice windows, silk and wood material detail, restrained negative space, classical elegance",
        negative="现代, 霓虹, 塑料",
        risk=3),

    # ---------- D 动画系 ----------
    "ANIME_CN": dict(
        name="国漫二维", group="D动画", tier="C",
        use_for="国漫改编、热血、玄幻（一致性靠线条，需写发型发色瞳色）",
        prompt_cn="国漫二维动画风格，清晰线条，明快色块，赛璐璐上色，中式审美的人物五官，背景有水墨晕染，动态张力",
        prompt_en="Chinese 2D animation style, clean linework, bright color blocks, cel shading, Chinese aesthetic facial features, ink-wash influenced backgrounds, dynamic energy",
        negative="真人, 写实, 3D",
        risk=3),
    "ANIME_JP": dict(
        name="日系动漫", group="D动画", tier="C",
        use_for="青春、校园、治愈",
        prompt_cn="日系动画风格，大眼睛角色设计，柔和渐层上色，天空与光晕细节丰富，清新通透的氛围，细腻的背景美术",
        prompt_en="Japanese anime style, large expressive eyes, soft gradient shading, detailed skies and light halos, fresh translucent atmosphere, delicate background art",
        negative="真人, 厚涂, 3D",
        risk=3),
    "PIXAR_3D": dict(
        name="3D皮克斯", group="D动画", tier="S",
        use_for="萌宝、合家欢、品牌吉祥物（3D 一致性比真人更好，适合量产）",
        prompt_cn="3D 动画电影质感，圆润可爱的造型设计，次表面散射的柔和皮肤，明亮饱和的色彩，细腻的毛发与布料，柔和的三点布光",
        prompt_en="3D animated feature look, rounded appealing character design, soft subsurface-scattering skin, bright saturated colors, detailed hair and cloth, soft three-point lighting",
        negative="真人, 二维, 写实皮肤",
        risk=3),
    "INK_WASH": dict(
        name="水墨", group="D动画", tier="C",
        use_for="古风意境、片头、情绪段落（人物脸易糊，只做空镜）",
        prompt_cn="中国水墨画风格，单色墨韵浓淡变化，大面积留白，笔触有呼吸感，宣纸纹理，淡彩点缀，意境空灵",
        prompt_en="Chinese ink wash painting style, monochrome ink gradation, large negative space, breathing brushstrokes, rice paper texture, faint color accents, ethereal mood",
        negative="鲜艳, 写实, 高细节",
        risk=4),
    "COMIC_CELL": dict(
        name="漫画分格", group="D动画", tier="C",
        use_for="漫剧、搞笑、快节奏（一集不超过 2 镜）",
        prompt_cn="漫画风格画面，粗黑描边，网点阴影，平涂色块，分格构图感，动态速度线，强烈图形化",
        prompt_en="comic book style, bold black outlines, halftone dot shading, flat color fills, panel composition feel, dynamic speed lines, strongly graphic",
        negative="写实, 柔光, 渐变",
        risk=3),
    "CLAY": dict(
        name="黏土定格", group="D动画", tier="C",
        use_for="萌系、搞笑、科普（极难稳定，建议只做单镜创意）",
        prompt_cn="黏土定格动画质感，手捏黏土的指纹与不规则边缘，微缩舞台布景，柔和棚内布光，温暖的拙趣感",
        prompt_en="claymation stop-motion look, visible fingerprints and irregular clay edges, miniature set design, soft studio lighting, warm handmade charm",
        negative="光滑, 3D 渲染完美, 写实",
        risk=4),

    # ---------- E 风格化视觉系 ----------
    "CYBERPUNK": dict(
        name="赛博朋克", group="E风格化", tier="B",
        use_for="未来都市、科技犯罪",
        prompt_cn="赛博朋克风格，雨夜潮湿街道，密集霓虹与全息广告牌，品红与青色强对比，地面积水强反射，烟雾与蒸汽，高科技低生活质感",
        prompt_en="cyberpunk style, rainy wet streets at night, dense neon and holographic billboards, strong magenta and cyan contrast, heavy puddle reflections, smoke and steam, high-tech low-life texture",
        negative="自然光, 田园, 干燥",
        risk=3),
    "GLITCH": dict(
        name="故障艺术", group="E风格化", tier="C",
        use_for="记忆闪回、系统入侵（只做单镜 ≤1.5s）",
        prompt_cn="故障艺术质感，画面撕裂与横向错位，RGB 色散分离，像素化区块，数据噪点，信号不稳的闪烁",
        prompt_en="glitch art look, image tearing and horizontal displacement, RGB chromatic separation, pixelated blocks, data noise, unstable signal flicker",
        negative="平稳, 干净, 写实",
        risk=5),
    "DREAMCORE": dict(
        name="梦境虚幻", group="E风格化", tier="B",
        use_for="梦境、回忆、心理戏",
        prompt_cn="梦境质感，柔和浓雾，无重力悬浮感，超现实的柔和色彩，光晕弥漫，边界模糊，安静而不真实",
        prompt_en="dreamcore look, soft dense haze, weightless floating feel, surreal pastel palette, pervasive glow, blurred boundaries, quiet and unreal",
        negative="锐利, 高对比, 现实感",
        risk=3),
    "NEON_NOIR": dict(
        name="霓虹黑色", group="E风格化", tier="B",
        use_for="都市犯罪、夜戏、反派登场",
        prompt_cn="霓虹黑色电影风格，黑色电影硬光结构，暗部渗入品红与青蓝霓虹，强对比，湿冷质感，烟雾在光柱里翻卷",
        prompt_en="neon noir look, film noir hard light structure, shadows infiltrated with magenta and cyan neon, strong contrast, cold damp texture, smoke curling in light beams",
        negative="平光, 明亮, 暖调",
        risk=3),

    # ---------- F 竖屏短剧特有 ----------
    "DOUYIN_HIGH": dict(
        name="抖音高清爽剧", group="F竖屏短剧", tier="S",
        use_for="逆袭打脸、爽剧、投流素材",
        prompt_cn="高清短剧质感，高锐度高饱和，干净简洁的背景，人物面部明亮立体，高对比清晰轮廓，画面通透，移动端第一眼抓人",
        prompt_en="HD short-drama look, high sharpness and saturation, clean simple background, brightly lit three-dimensional face, high-contrast crisp outline, clear transparent image, eye-catching on mobile at first glance",
        negative="灰蒙, 低对比, 老电影感",
        risk=2),
    "DRAMA_SOFT": dict(
        name="柔光短剧", group="F竖屏短剧", tier="S",
        use_for="甜宠、家庭、治愈",
        prompt_cn="柔光短剧质感，均匀柔和的布光，通透好气色的肤色，温和低反差，干净构图，无攻击性的观感",
        prompt_en="soft-light short-drama look, even diffused lighting, clear healthy skin tone, gentle low contrast, clean composition, non-aggressive visual feel",
        negative="硬光, 强对比, 阴森",
        risk=2),
    "RAW_PHONE": dict(
        name="手机原生感", group="F竖屏短剧", tier="B",
        use_for="伪素人、探店、真实故事",
        prompt_cn="手机拍摄原生质感，竖屏手持构图，自然光源，轻微过曝与抖动，真实不做作的色彩，社交平台原生感",
        prompt_en="native smartphone footage look, vertical handheld framing, available light, slight overexposure and shake, authentic unpolished color, social-platform native feel",
        negative="电影感, 专业布光, 三脚架稳定",
        risk=3),
    "DRAMA_DARK": dict(
        name="暗黑反转", group="F竖屏短剧", tier="B",
        use_for="复仇、反转、反派主场（暗部要写保留细节）",
        prompt_cn="暗黑短剧质感，整体低亮度，单点侧光照亮半张脸，深黑背景，冷调，高反差，压迫与危险感，暗部保留细节",
        prompt_en="dark short-drama look, overall low brightness, single side light illuminating half the face, deep black background, cool grade, high contrast, oppressive and dangerous, shadows retain detail",
        negative="明亮, 均匀布光, 阳光",
        risk=3),
}

# ============================================================
# 修饰层（0–2 个）
# ============================================================
OVERLAYS: dict[str, dict] = {
    # 光线层
    "GLOW_LIGHT": dict(kind="光线", name="柔和光辉",
                       cn="柔和光辉弥漫，逆光轮廓光，空气中有光晕",
                       en="soft pervasive glow, backlit rim light, halo in the air",
                       use_for="甜宠、回忆"),
    "CONTRAST_HIGH": dict(kind="光线", name="高对比硬光",
                          cn="高对比硬光，明确光源方向，深黑暗部",
                          en="high-contrast hard light, clear light direction, deep black shadows",
                          use_for="打脸、冲突"),
    "WINDOW_LIGHT": dict(kind="光线", name="窗光斜射",
                         cn="窗光斜射，光柱可见，尘埃浮动",
                         en="angled window light, visible light shaft, floating dust",
                         use_for="室内、怀旧"),
    "NEON_LIGHT": dict(kind="光线", name="霓虹多色",
                       cn="霓虹多色光源，品红青蓝交织，湿面反光",
                       en="multi-color neon sources, magenta cyan blue interweaving, wet surface reflections",
                       use_for="夜戏、赛博"),
    "CANDLE_LIGHT": dict(kind="光线", name="烛火暖光",
                         cn="烛火暖光，光源摇曳，暖橙光晕",
                         en="candlelight warm glow, flickering source, warm orange halo",
                         use_for="古装、亲密"),
    "OVERCAST_LIGHT": dict(kind="光线", name="阴天散射",
                           cn="阴天散射光，无硬阴影，平淡真实",
                           en="overcast diffused light, no hard shadows, flat realistic",
                           use_for="纪实、压抑"),
    # 后期层
    "FILM_GRAIN": dict(kind="后期", name="胶片颗粒",
                       cn="明显胶片颗粒，轻微画面呼吸感",
                       en="visible film grain, subtle frame breathing",
                       use_for="复古/电影系"),
    "GRADE_COLD": dict(kind="后期", name="冷调调色",
                       cn="冷调调色，青蓝倾向，低饱和",
                       en="cool grade, cyan-blue cast, low saturation",
                       use_for="复仇、悬疑"),
    "GRADE_WARM": dict(kind="后期", name="暖调调色",
                       cn="暖调调色，琥珀金倾向",
                       en="warm grade, amber gold cast",
                       use_for="家庭、怀旧"),
    "HALATION": dict(kind="后期", name="高光溢出",
                     cn="高光溢出光晕，柔和边缘发光",
                     en="highlight bloom halo, soft edge glow",
                     use_for="甜宠、回忆"),
    "BLEACH_BYPASS": dict(kind="后期", name="漂白高反差",
                          cn="漂白高反差，低饱和高对比，银盐感",
                          en="bleach bypass, low saturation high contrast, silver halide feel",
                          use_for="战争、粗粝"),
    "VIGNETTE": dict(kind="后期", name="四角暗角",
                     cn="四角暗角，视线聚焦中心",
                     en="corner vignette, focus toward center",
                     use_for="悬疑、情绪"),
    # 媒介层
    "MED_VHS": dict(kind="媒介", name="VHS 媒介",
                    cn="VHS 扫描线与磁带噪",
                    en="VHS scanlines and tape noise", use_for="伪纪录、恐怖"),
    "MED_16MM": dict(kind="媒介", name="16mm 媒介",
                     cn="16mm 颗粒与划痕",
                     en="16mm grain and scratches", use_for="独立电影感"),
    "MED_CRT": dict(kind="媒介", name="CRT 媒介",
                    cn="CRT 圆角屏幕与扫描线",
                    en="CRT rounded screen and scanlines", use_for="年代回忆"),
    "MED_POLAROID": dict(kind="媒介", name="宝丽来媒介",
                         cn="宝丽来白边与偏色",
                         en="Polaroid white border and color shift", use_for="插入定帧"),
}

# 题材 → 推荐风格
TOPIC_RECOMMEND = {
    "都市甜宠": ("ROMANCE_SOFT", ["GLOW_LIGHT"]),
    "逆袭打脸": ("DOUYIN_HIGH", ["CONTRAST_HIGH"]),
    "复仇爽剧": ("CINEMA_COLD", ["FILM_GRAIN"]),
    "战神归来": ("CINEMA_REAL", ["ANAMORPHIC"]),
    "重生90年代": ("RETRO_90S_CN", ["GRADE_WARM"]),
    "港风怀旧": ("RETRO_HK", ["FILM_GRAIN"]),
    "婆媳家庭": ("DOC_REAL", []),
    "悬疑反转": ("SUSPENSE_DARK", ["GRADE_COLD"]),
    "古风宅斗": ("ANCIENT_CN", ["CANDLE_LIGHT"]),
    "萌宝": ("PIXAR_3D", ["GLOW_LIGHT"]),
    "国漫改编": ("ANIME_CN", []),
    "赛博未来": ("CYBERPUNK", ["NEON_LIGHT"]),
    "战争年代": ("WAR_DESAT", ["FILM_GRAIN"]),
    "产品带货": ("TEAL_ORANGE", ["MACRO_TEXTURE"] if False else ["FILM_GRAIN"]),
}

MAX_OVERLAYS = 2


# ============================================================
# 拼装
# ============================================================
def build_style_prompt(style_id: str, overlays: list[str] | None = None,
                       lang: str = "cn") -> str:
    """生成 STYLE_PROMPT（含修饰层），用于拼进 first_frame_prompt"""
    if style_id not in STYLES:
        raise KeyError(f"未知风格 {style_id}")
    st = STYLES[style_id]
    overlays = overlays or []
    if len(overlays) > MAX_OVERLAYS:
        raise ValueError(f"修饰层最多 {MAX_OVERLAYS} 个，当前 {len(overlays)}")

    parts = [st["prompt_cn"] if lang == "cn" else st["prompt_en"]]
    for o in overlays:
        if o not in OVERLAYS:
            raise KeyError(f"未知修饰层 {o}")
        parts.append(OVERLAYS[o]["cn"] if lang == "cn" else OVERLAYS[o]["en"])
    return "，".join(parts)


def build_negative(style_id: str, overlays: list[str] | None = None) -> str:
    """风格负向词（已含修饰层对应抑制词）"""
    st = STYLES[style_id]
    parts = [st["negative"]]
    # 媒介层需要压制品模型"自作主张变高清"
    if overlays and any(o.startswith("MED_") for o in overlays):
        parts.append("高清, 4K, 锐利, 无噪点")
    return ", ".join(parts)


# 风格层与通用画质后缀的重叠词（避免同一形容词出现两次稀释权重）
_STYLE_OVERLAP_WITH_QUALITY = {
    "电影感", "电影感画面", "35mm 胶片质感", "35mm胶片质感", "浅景深",
    "高细节皮肤纹理", "自然光", "胶片颗粒", "明显胶片颗粒",
}


def quality_suffix(style_id: str = "", overlays: list[str] | None = None,
                   lang: str = "cn") -> str:
    """生成最终画质后缀：与风格层去重后保留风格特有描述。

    问题背景：风格层里已有"35mm胶片质感/浅景深/电影感"，
    通用后缀再写一遍会让模型把权重分散，也会浪费 token。
    这里从后缀里剔除已被风格层覆盖的词，只保留风格层没有的（如 8k/竖构图）。
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import QUALITY_SUFFIX_CN, dedupe_csv

    if not style_id or style_id not in STYLES:
        return QUALITY_SUFFIX_CN

    sp = build_style_prompt(style_id, overlays, lang)
    # 抽出后缀里的每一项，若其核心词已出现在风格层，就丢弃
    keep = []
    for item in [x.strip() for x in QUALITY_SUFFIX_CN.split(",") if x.strip()]:
        core = item.replace(" ", "")
        covered = any(core in sp.replace(" ", "")
                      or kw.replace(" ", "") in core
                      for kw in _STYLE_OVERLAP_WITH_QUALITY)
        if not covered:
            keep.append(item)
    # 必留项：分辨率与大画幅信息
    for must in ("8k", "竖构图9:16"):
        if must not in keep:
            keep.append(must)
    return dedupe_csv(", ".join(keep))


def validate(style_id: str, overlays: list[str], topic: str | None = None) -> list[str]:
    """返回问题列表（空 = 通过）"""
    errs = []
    if style_id not in STYLES:
        errs.append(f"未知风格 {style_id}")
        return errs
    if len(overlays) > MAX_OVERLAYS:
        errs.append(f"修饰层 {len(overlays)} 个 > 上限 {MAX_OVERLAYS}")
    for o in overlays:
        if o not in OVERLAYS:
            errs.append(f"未知修饰层 {o}")
    # 同一类修饰层不许叠两个
    kinds = [OVERLAYS[o]["kind"] for o in overlays if o in OVERLAYS]
    if len(kinds) != len(set(kinds)):
        errs.append(f"同类修饰层重复（光线/后期/媒介 各最多 1 个）：{kinds}")
    # 与题材匹配性提醒（非致命）
    if topic and topic in TOPIC_RECOMMEND:
        rec, _ = TOPIC_RECOMMEND[topic]
        if style_id != rec and STYLES[style_id]["tier"] == "C":
            errs.append(f"题材「{topic}」推荐 {rec}，当前选了 C 档风格 "
                        f"{style_id}（一致性低，抽卡成本高）")
    return errs


def tier_of(style_id: str) -> str:
    return STYLES.get(style_id, {}).get("tier", "?")


def list_by_group() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for sid, st in STYLES.items():
        out.setdefault(st["group"], []).append(sid)
    return out


if __name__ == "__main__":
    print(f"风格总数 {len(STYLES)} | 修饰层 {len(OVERLAYS)}")
    for grp, ids in list_by_group().items():
        print(f"\n{grp}（{len(ids)}）")
        for sid in ids:
            st = STYLES[sid]
            print(f"  [{st['tier']}] {sid:<16} {st['name']}  — {st['use_for']}")
    print("\n示例拼装：")
    print(build_style_prompt("CINEMA_REAL", ["FILM_GRAIN", "WINDOW_LIGHT"]))
