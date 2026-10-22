import os
import sys
import uuid
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, delete
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    # 1. 删除诺姆的重火力型与狙击型
    to_delete = ["诺姆 GNOME（重火力型）", "诺姆 GNOME（狙击型）"]
    for name in to_delete:
        item = session.scalars(
            select(Product).where(
                Product.manufacturer == "伊达斯科技",
                Product.kit_name == name,
            )
        ).first()
        if item:
            session.delete(item)
            print(f"Deleted: {name}")

    # 2. 阿斯加德限定拆分
    asgard_combined = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "阿斯加德 ASGARD（会场限定机械透明/彩透版）",
        )
    ).first()
    if asgard_combined:
        asgard_combined.kit_name = "阿斯加德 ASGARD（会场限定机械透明版）"
        asgard_combined.detail = "会场限定机械透明外甲版本，透视展示四层复杂骨架与联动机械结构。"
        print("Updated: 阿斯加德 ASGARD（会场限定机械透明版）")

    # 检查并添加会场限定彩透版
    asgard_caitou = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "阿斯加德 ASGARD（会场限定彩透版）",
        )
    ).first()
    if not asgard_caitou:
        session.add(
            Product(
                id=uuid.uuid4(),
                manufacturer="伊达斯科技",
                product_code=None,
                product_line="1/100",
                kit_name="阿斯加德 ASGARD（会场限定彩透版）",
                origin_type="手动录入",
                source="手动录入",
                detail="会场限定彩色透明外甲版本，兼顾分色层次与骨架内构透光观赏性。",
            )
        )
        print("Added: 阿斯加德 ASGARD（会场限定彩透版）")

    # 3. 瓦尔基里限定拆分
    valk_combined = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "瓦尔基里 VALKYRIE（WF限定机械透明/全息影像版）",
        )
    ).first()
    if valk_combined:
        valk_combined.kit_name = "瓦尔基里 VALKYRIE（WF限定机械透明版）"
        valk_combined.detail = "WF展会限定机械透明版本（约258元档），透明外甲透视展示锌合金+POM骨架与细节。"
        print("Updated: 瓦尔基里 VALKYRIE（WF限定机械透明版）")

    valk_hologram = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "瓦尔基里 VALKYRIE（WF限定全息影像版）",
        )
    ).first()
    if not valk_hologram:
        session.add(
            Product(
                id=uuid.uuid4(),
                manufacturer="伊达斯科技",
                product_code=None,
                product_line="1/100",
                kit_name="瓦尔基里 VALKYRIE（WF限定全息影像版）",
                origin_type="手动录入",
                source="手动录入",
                detail="WF展会限定全息影像特殊质感版本（约258元档），呈现全息渐变光泽与未来科幻质感。",
            )
        )
        print("Added: 瓦尔基里 VALKYRIE（WF限定全息影像版）")

    # 4. 萨拉曼德限定拆分
    salamander_combined = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "萨拉曼德－火蛇（曜影/暗影抛光镀银版）",
        )
    ).first()
    if salamander_combined:
        salamander_combined.kit_name = "萨拉曼德－火蛇（曜影版/抛光镀银）"
        salamander_combined.detail = "曜影换色版，抛光镀银钛金属质感涂装，定价188元，限量1500体。"
        print("Updated: 萨拉曼德－火蛇（曜影版/抛光镀银）")

    salamander_dark = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "萨拉曼德－火蛇（暗影版/曜银抛光镀银）",
        )
    ).first()
    if not salamander_dark:
        session.add(
            Product(
                id=uuid.uuid4(),
                manufacturer="伊达斯科技",
                product_code=None,
                product_line="1/100",
                kit_name="萨拉曼德－火蛇（暗影版/曜银抛光镀银）",
                origin_type="手动录入",
                source="手动录入",
                detail="暗影版（曜银），抛光镀银钛金属质感深色涂装，定价188元，限量1500体。",
            )
        )
        print("Added: 萨拉曼德－火蛇（暗影版/曜银抛光镀银）")

    # 5. 更新诺姆队长机名称和描述，更精准
    gnome_first = session.scalars(
        select(Product).where(
            Product.manufacturer == "伊达斯科技",
            Product.kit_name == "诺姆 GNOME（量产型/队长机）",
        )
    ).first()
    if gnome_first:
        gnome_first.detail = "定价168元，高约19cm（2026年7月）。队长机普通版量产机体，经实拍调深改色，质感表现优良。"

    session.commit()
    print("\nAll adjustments successfully committed.")
