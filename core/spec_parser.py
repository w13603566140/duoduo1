"""
从商品标题中提取规格信息
"""
import re


def extract_specs(product_name: str) -> str:
    """
    从拼多多商品标题中提取规格信息。
    返回规格字符串，如 "220g; 袋装; 纯莜面; 低脂"
    """
    if not product_name:
        return ""

    specs = []
    name = product_name

    # 1. 重量/容量
    weight = _extract_weight(name)
    if weight:
        specs.append(weight)

    # 2. 包装形式
    packages = _extract_package(name)
    specs.extend(packages)

    # 3. 品类特征
    types = _extract_types(name)
    for t in types:
        if t not in specs:
            specs.append(t)

    return '; '.join(specs[:6])


def _extract_weight(name: str) -> str:
    """提取重量信息"""
    # 带单位的重量: 220g, 248g/袋, 500g, 2.5kg, 1斤
    patterns = [
        (r'(\d+\.?\d*)\s*g', 'g'),       # 220g, 248g
        (r'(\d+\.?\d*)\s*kg', 'kg'),     # 2.5kg
        (r'(\d+\.?\d*)\s*斤', '斤'),      # 1斤
        (r'(\d+)\s*克', 'g'),             # 220克
    ]
    for pat, unit in patterns:
        m = re.search(pat, name, re.IGNORECASE)
        if m:
            return m.group(1) + unit

    # 末尾纯数字可能是克数: "莜面鱼鱼120" -> 120g
    m = re.search(r'(\d{2,4})$', name)
    if m:
        num = int(m.group(1))
        if 100 <= num <= 5000:  # 合理克数范围
            return m.group(1) + 'g'

    return ""


def _extract_package(name: str) -> list:
    """提取包装形式"""
    packages = []

    package_keywords = [
        ('真空', '真空包装'),
        ('袋装', '袋装'),
        ('盒装', '盒装'),
        ('箱装', '箱装'),
        ('桶装', '桶装'),
        ('散装', '散装'),
        ('独立包装', '独立包装'),
        ('大袋', '袋装'),
        ('小袋', '袋装'),
    ]

    for kw, label in package_keywords:
        if kw in name and label not in packages:
            packages.append(label)

    # 数量+包装单位: 5袋, 2盒, 3箱
    m = re.search(r'(\d+)\s*(袋|盒|箱|桶|包|瓶|罐)', name)
    if m:
        pkg = '{}装'.format(m.group(0).replace(' ', ''))
        if pkg not in packages:
            packages.append(pkg)

    return packages[:2]  # 最多2个包装标签


def _extract_types(name: str) -> list:
    """提取品类特征"""
    types = []

    type_patterns = [
        # 原料
        (r'纯莜面|纯莜麦', '纯莜面'),
        (r'荞麦|荞面', '荞麦'),
        (r'燕麦', '燕麦'),
        (r'粗粮|杂粮', '粗粮'),
        (r'山药', '山药'),
        (r'果蔬|蔬菜', '果蔬'),
        # 健康属性
        (r'低脂|脱脂|无脂', '低脂'),
        (r'无糖|低糖|代糖', '低糖'),
        (r'高纤维|高膳食', '高纤维'),
        # 工艺
        (r'手工|手搓|传统工艺', '手工'),
        (r'真空|冻干', '真空'),
        (r'有机|绿色', '有机'),
        # 食用方式
        (r'速食|速冻|即食|方便', '速食'),
        (r'熟食|开袋即食', '熟食'),
        (r'代餐', '代餐'),
        (r'健身|减脂|轻食', '健身'),
        (r'凉拌|汤面|炒面', '烹饪'),
        (r'早餐|早晚餐', '早餐'),
        # 其他
        (r'新鲜|现做', '新鲜'),
        (r'儿童|宝宝', '儿童'),
        (r'特产', '特产'),
    ]

    for pat, label in type_patterns:
        if re.search(pat, name) and label not in types:
            types.append(label)

    return types[:4]  # 最多4个品类标签


def generate_product_link(keyword: str, rank: int) -> str:
    """生成拼多多搜索链接"""
    return 'https://mobile.yangkeduo.com/search_result.html?search_key={}&search_type=goods'.format(
        keyword
    )
