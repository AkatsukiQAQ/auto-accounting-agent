"""Seed brands for the target geography (JP-heavy + CN + global).

Idempotent by id: `ensure_seed_merchants` inserts only missing rows on every
boot, so user edits to existing rows are never overwritten. Aliases are
matched case- and whitespace-insensitively by the engine's brand lookup.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Merchant


@dataclass(frozen=True)
class _MerchantSpec:
    id: str
    canonical_name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    default_category_id: str | None = None


_SPECS: tuple[_MerchantSpec, ...] = (
    # ── Japan: convenience / supermarket ──
    _MerchantSpec("seven-eleven", "7-Eleven", ("セブンイレブン", "セブン-イレブン", "セブン‐イレブン", "711"), "food"),
    _MerchantSpec("family-mart", "FamilyMart", ("ファミリーマート", "ファミマ", "Family Mart"), "food"),
    _MerchantSpec("lawson", "Lawson", ("ローソン", "ナチュラルローソン"), "food"),
    _MerchantSpec("ministop", "Ministop", ("ミニストップ",), "food"),
    _MerchantSpec("keikyu-store", "Keikyu Store", ("京急ストア", "けいきゅうストア"), "food"),
    _MerchantSpec("seiyu", "Seiyu", ("西友",), "food"),
    _MerchantSpec("ito-yokado", "Ito-Yokado", ("イトーヨーカドー", "イトーヨーカ堂"), "food"),
    _MerchantSpec("aeon", "AEON", ("イオン", "AEON MALL", "イオンモール"), "food"),
    _MerchantSpec("ozeki", "Ozeki", ("オオゼキ",), "food"),
    _MerchantSpec("gyomu-super", "Gyomu Super", ("業務スーパー",), "food"),
    # ── Japan: restaurants / cafés ──
    _MerchantSpec("starbucks", "Starbucks", ("スターバックス", "スタバ", "星巴克", "Starbucks Coffee"), "food"),
    _MerchantSpec("doutor", "Doutor", ("ドトール", "ドトールコーヒー"), "food"),
    _MerchantSpec("mcdonalds", "McDonald's", ("マクドナルド", "マック", "麦当劳", "McDonalds"), "food"),
    _MerchantSpec("kfc", "KFC", ("ケンタッキー", "肯德基", "Kentucky Fried Chicken"), "food"),
    _MerchantSpec("sukiya", "Sukiya", ("すき家",), "food"),
    _MerchantSpec("yoshinoya", "Yoshinoya", ("吉野家",), "food"),
    _MerchantSpec("matsuya", "Matsuya", ("松屋",), "food"),
    _MerchantSpec("saizeriya", "Saizeriya", ("サイゼリヤ", "萨莉亚"), "food"),
    _MerchantSpec("gusto", "Gusto", ("ガスト",), "food"),
    _MerchantSpec("coco-ichibanya", "CoCo Ichibanya", ("CoCo壱番屋", "ココイチ", "カレーハウスCoCo壱番屋"), "food"),
    _MerchantSpec("ichiran", "Ichiran", ("一蘭", "一兰"), "food"),
    # ── Japan: delivery ──
    _MerchantSpec("uber-eats", "Uber Eats", ("UberEats", "ウーバーイーツ"), "food"),
    _MerchantSpec("demae-can", "Demae-can", ("出前館",), "food"),
    # ── Japan: retail / drugstore ──
    _MerchantSpec("uniqlo", "Uniqlo", ("ユニクロ", "优衣库"), "shopping"),
    _MerchantSpec("gu", "GU", ("ジーユー",), "shopping"),
    _MerchantSpec("muji", "MUJI", ("無印良品", "无印良品"), "shopping"),
    _MerchantSpec("don-quijote", "Don Quijote", ("ドン・キホーテ", "ドンキホーテ", "ドンキ", "唐吉诃德"), "shopping"),
    _MerchantSpec("daiso", "Daiso", ("ダイソー", "大創", "大创"), "shopping"),
    _MerchantSpec("nitori", "Nitori", ("ニトリ",), "shopping"),
    _MerchantSpec("bic-camera", "Bic Camera", ("ビックカメラ",), "shopping"),
    _MerchantSpec("yodobashi", "Yodobashi Camera", ("ヨドバシカメラ", "ヨドバシ"), "shopping"),
    _MerchantSpec("matsumoto-kiyoshi", "Matsumoto Kiyoshi", ("マツモトキヨシ", "マツキヨ"), "health"),
    _MerchantSpec("welcia", "Welcia", ("ウエルシア",), "health"),
    # ── Japan: transport ──
    _MerchantSpec("jr-east", "JR East", ("JR東日本", "JR EAST", "East Japan Railway"), "transport"),
    _MerchantSpec("suica", "Suica", ("スイカ", "Suicaチャージ"), "transport"),
    _MerchantSpec("pasmo", "PASMO", ("パスモ",), "transport"),
    _MerchantSpec("tokyo-metro", "Tokyo Metro", ("東京メトロ", "東京地下鉄"), "transport"),
    _MerchantSpec("keikyu", "Keikyu", ("京急", "京浜急行"), "transport"),
    # ── China ──
    _MerchantSpec("meituan", "美团", ("Meituan", "美团外卖"), "food"),
    _MerchantSpec("eleme", "饿了么", ("Eleme", "ele.me"), "food"),
    _MerchantSpec("taobao", "淘宝", ("Taobao",), "shopping"),
    _MerchantSpec("jd", "京东", ("JD", "JD.com", "jd.com"), "shopping"),
    _MerchantSpec("pinduoduo", "拼多多", ("Pinduoduo", "PDD"), "shopping"),
    _MerchantSpec("didi", "滴滴", ("DiDi", "滴滴出行"), "transport"),
    _MerchantSpec("alipay", "支付宝", ("Alipay",), None),
    _MerchantSpec("wechat-pay", "微信支付", ("WeChat Pay", "Weixin Pay", "微信"), None),
    # ── Global ──
    _MerchantSpec("amazon", "Amazon", ("アマゾン", "亚马逊", "Amazon.co.jp", "AMZN"), "shopping"),
    _MerchantSpec("apple", "Apple", ("アップル", "苹果", "Apple.com"), "shopping"),
    _MerchantSpec("google", "Google", ("グーグル", "Google Play"), None),
    _MerchantSpec("netflix", "Netflix", ("ネットフリックス",), "entertain"),
    _MerchantSpec("spotify", "Spotify", (), "entertain"),
    _MerchantSpec("steam", "Steam", (), "entertain"),
    _MerchantSpec("nintendo", "Nintendo", ("任天堂", "Nintendo eShop"), "entertain"),
    _MerchantSpec("playstation", "PlayStation", ("プレイステーション", "PlayStation Store"), "entertain"),
    _MerchantSpec("uber", "Uber", (), "transport"),
    _MerchantSpec("ikea", "IKEA", ("イケア", "宜家"), "shopping"),
)


def ensure_seed_merchants(session: Session) -> int:
    """Insert missing seed brands (idempotent, never overwrites existing rows)."""
    existing: set[str] = set(session.scalars(select(Merchant.id)).all())
    inserted = 0
    for spec in _SPECS:
        if spec.id in existing:
            continue
        session.add(
            Merchant(
                id=spec.id,
                canonical_name=spec.canonical_name,
                aliases=list(spec.aliases),
                default_category_id=spec.default_category_id,
                source="seed",
            )
        )
        inserted += 1
    if inserted:
        session.flush()
    return inserted
