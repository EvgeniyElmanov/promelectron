"""Self-contained тесты для scripts/onec_format_analyzer.py.

Без БД/app-фикстур: скрипт загружается через importlib по пути,
используются только tmp_path, monkeypatch и inline-фикстуры.
"""

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

def _find_script() -> Path | None:
    """Ищет scripts/onec_format_analyzer.py вверх от теста.

    В docker-окружении `make test-backend` монтируется только backend/ —
    тогда модуль пропускается (реальные прогоны — из venv на хосте).
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "scripts" / "onec_format_analyzer.py"
        if candidate.is_file():
            return candidate
    return None


SCRIPT_PATH = _find_script()
if SCRIPT_PATH is None:
    pytest.skip(
        "scripts/onec_format_analyzer.py недоступен в этом окружении",
        allow_module_level=True,
    )

spec = importlib.util.spec_from_file_location("onec_format_analyzer", SCRIPT_PATH)
ofa = importlib.util.module_from_spec(spec)
sys.modules.setdefault("onec_format_analyzer", ofa)
spec.loader.exec_module(ofa)

# ─── Inline-фикстуры ─────────────────────────────────────────────────────────

PRODUCT_GUID = "18f0067f-c41b-4e0a-bb07-efea606525c1"
ATTR_GUID = "7ffcb01d-9f4b-11eb-80ca-d45d647f1831"
VALUE_GUID = "d7c8435d-a19a-11eb-80ca-d45d647f1831"
BROKEN_GUID = "aaaaaaaa-1111-2222-3333-444444444444"

METADATA_BASE = "http://example/odata/standard.odata/$metadata#"


def make_odata(entity: str, records: list[dict]) -> bytes:
    return json.dumps(
        {"odata.metadata": METADATA_BASE + entity, "value": records},
        ensure_ascii=False,
    ).encode()


@pytest.fixture()
def products_json() -> bytes:
    return make_odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": PRODUCT_GUID,
                "Description": "Кабель 2х0,50",
                "IsFolder": False,
                "DeletionMark": False,
                "ТипНоменклатуры": "Запас",
                "Parent_Key": ofa.NULL_GUID,
            },
            {
                "Ref_Key": "bd1060d4-71a8-11eb-80d4-00155d006601",
                "Description": "Удалённый",
                "IsFolder": False,
                "DeletionMark": True,
                "ТипНоменклатуры": "Запас",
                "Parent_Key": ofa.NULL_GUID,
            },
            {
                "Ref_Key": "3a2f9e81-71a9-11eb-80d4-00155d006601",
                "Description": "Папка",
                "IsFolder": True,
                "DeletionMark": False,
                "Parent_Key": ofa.NULL_GUID,
            },
        ],
    )


@pytest.fixture()
def attribute_defs_json() -> bytes:
    return make_odata(
        "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения",
        [
            {
                "Ref_Key": ATTR_GUID,
                "Description": "Сечение",
                "DeletionMark": False,
                "ValueType": {"Types": ["CatalogRef.ЗначенияСвойствОбъектов"]},
            },
            {
                "Ref_Key": "11111111-9f4b-11eb-80ca-d45d647f1831",
                "Description": "Вес в упаковке",
                "DeletionMark": False,
                "ValueType": {"Types": ["Number"]},
            },
        ],
    )


@pytest.fixture()
def property_values_json() -> bytes:
    return make_odata(
        "Catalog_ЗначенияСвойствОбъектов",
        [
            {"Ref_Key": VALUE_GUID, "Description": "10,0мм2", "Owner_Key": ATTR_GUID},
            {
                "Ref_Key": "ec98534a-7d67-11eb-80bc-94de80b28a88",
                "Description": "16,0мм2",
                "Owner_Key": ATTR_GUID,
            },
        ],
    )


@pytest.fixture()
def product_attributes_json() -> bytes:
    return make_odata(
        "Catalog_Номенклатура_ДополнительныеРеквизиты",
        [
            {
                "Ref_Key": "cfb4c4ec-8652-460f-8007-af5e12d09811",
                "Свойство_Key": ATTR_GUID,
                "Значение": VALUE_GUID,
                "Значение_Type": "StandardODATA.Catalog_ЗначенияСвойствОбъектов",
                "ТекстоваяСтрока": "",
            },
            {
                "Ref_Key": "cfb4c4ec-8652-460f-8007-af5e12d09812",
                "Свойство_Key": ATTR_GUID,
                "Значение": "ec98534a-7d67-11eb-80bc-94de80b28a88",
                "Значение_Type": "StandardODATA.Catalog_ЗначенияСвойствОбъектов",
                "ТекстоваяСтрока": "",
            },
        ],
    )


CML_IMPORT = """<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10">
  <Каталог><Товары>
    <Товар><Ид>1</Ид><Наименование>Кабель</Наименование></Товар>
  </Товары></Каталог>
</КоммерческаяИнформация>""".encode()

CML_OFFERS = """<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10">
  <ПакетПредложений><Предложения>
    <Предложение><Ид>1</Ид><Цена>100</Цена></Предложение>
  </Предложения></ПакетПредложений>
</КоммерческаяИнформация>""".encode()


# ─── detect_format ───────────────────────────────────────────────────────────


class TestDetectFormat:
    def test_zip_by_magic(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("import.xml", "<xml/>")
        assert ofa.detect_format("dump.zip", buf.getvalue()) == "zip"

    def test_odata_json(self, products_json):
        assert ofa.detect_format("products.json", products_json) == "odata_json"

    def test_odata_error_json(self):
        data = json.dumps({"odata.error": {"code": "8", "message": {}}}).encode()
        assert ofa.detect_format("err.json", data) == "odata_json"

    def test_plain_json(self):
        assert ofa.detect_format("cfg.json", b'{"foo": 1}') == "json"

    def test_commerceml(self):
        assert ofa.detect_format("import.xml", CML_IMPORT) == "commerceml"

    def test_plain_xml(self):
        assert ofa.detect_format("metadata.xml", b"<Edmx/>") == "xml"

    def test_unknown(self):
        assert ofa.detect_format("dump.dat", b"\x00\x01\x02") == "unknown"


# ─── classify_odata_entity ───────────────────────────────────────────────────


class TestClassifyOdataEntity:
    def test_plain_entity(self):
        url = METADATA_BASE + "Catalog_Номенклатура"
        assert ofa.classify_odata_entity(url) == "Catalog_Номенклатура"

    def test_collection_wrapper(self):
        url = (
            METADATA_BASE
            + "Collection(StandardODATA.AccumulationRegister_ЗапасыНаСкладах_Balance)"
        )
        assert (
            ofa.classify_odata_entity(url)
            == "AccumulationRegister_ЗапасыНаСкладах_Balance"
        )

    def test_element_suffix(self):
        url = METADATA_BASE + "Catalog_НоменклатураПрисоединенныеФайлы/@Element"
        assert (
            ofa.classify_odata_entity(url) == "Catalog_НоменклатураПрисоединенныеФайлы"
        )


# ─── classify_cml_role ───────────────────────────────────────────────────────


class TestClassifyCmlRole:
    def test_import(self):
        root = ofa.ElementTree.fromstring(CML_IMPORT)
        assert ofa.classify_cml_role(root) == "import"

    def test_offers(self):
        root = ofa.ElementTree.fromstring(CML_OFFERS)
        assert ofa.classify_cml_role(root) == "offers"


# ─── ZIP ─────────────────────────────────────────────────────────────────────


class TestZip:
    def test_extract_zip_recursive(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as zf:
            zf.writestr("inner.json", "{}")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w") as zf:
            zf.writestr("data.json", "{}")
            zf.writestr("nested.zip", inner.getvalue())
        items = ofa.extract_zip("dump.zip", outer.getvalue())
        names = {name for name, _ in items}
        assert names == {"dump.zip!data.json", "dump.zip!nested.zip!inner.json"}


# ─── analyze_records / правило «активные» (D-09) ─────────────────────────────


class TestAnalyzeRecords:
    def test_products_active_rule(self, products_json):
        records = json.loads(products_json)["value"]
        stats = ofa.analyze_records(records, "products")
        assert stats["total"] == 3
        # активна только «Запас» без DeletionMark и не папка
        assert stats["active"] == 1
        assert stats["filtered_out"] == 2
        assert stats["fields"]["Description"]["fill_rate"] == 1.0

    def test_prices_active_rule(self):
        records = [
            {"Цена": 100, "Актуальность": True, "DeletionMark": False},
            {"Цена": 200, "Актуальность": False, "DeletionMark": False},
        ]
        stats = ofa.analyze_records(records, "prices")
        assert stats["active"] == 1

    def test_fill_rate_and_distinct(self):
        records = [{"a": 1, "b": None}, {"a": 2}, {"a": 2, "b": "x"}]
        stats = ofa.analyze_records(records, "other")
        assert stats["fields"]["a"]["distinct"] == 2
        assert stats["fields"]["b"]["fill_rate"] == pytest.approx(0.3333)


# ─── analyze_attributes ──────────────────────────────────────────────────────


class TestAnalyzeAttributes:
    def test_join_and_numeric_candidates(
        self, attribute_defs_json, product_attributes_json, property_values_json
    ):
        result = ofa.analyze_attributes(
            json.loads(attribute_defs_json)["value"],
            json.loads(product_attributes_json)["value"],
            json.loads(property_values_json)["value"],
        )
        assert result["total_assignments"] == 2
        attr = next(a for a in result["attributes"] if a["guid"] == ATTR_GUID)
        assert attr["name"] == "Сечение"
        assert attr["value_type"] == "enum"
        assert attr["numeric_candidate"] is True
        assert attr["numeric_unit"] == "мм²"
        numbers = {e["number"] for e in attr["numeric_examples"]}
        assert numbers == {10.0, 16.0}
        top_values = {v["value"] for v in attr["top_values"]}
        assert "10,0мм2" in top_values

    def test_literal_value_not_guid(self, attribute_defs_json, property_values_json):
        assignments = [
            {
                "Ref_Key": "cfb4c4ec-8652-460f-8007-af5e12d09811",
                "Свойство_Key": ATTR_GUID,
                "Значение": "просто текст",
                "ТекстоваяСтрока": "",
            }
        ]
        result = ofa.analyze_attributes(
            json.loads(attribute_defs_json)["value"],
            assignments,
            json.loads(property_values_json)["value"],
        )
        attr = result["attributes"][0]
        assert attr["top_values"][0]["value"] == "просто текст"
        assert attr["numeric_candidate"] is False

    def test_numeric_value_re(self):
        assert ofa.parse_numeric_candidate("10,0мм2") == (10.0, "мм²")
        assert ofa.parse_numeric_candidate("1шт") == (1.0, "шт")
        assert ofa.parse_numeric_candidate("медь") is None

    def test_numeric_candidates_from_property_value_owners(
        self, attribute_defs_json, property_values_json
    ):
        """На обрезанных сэмплах назначений нет — кандидаты ищутся по Owner_Key."""
        result = ofa.analyze_attributes(
            json.loads(attribute_defs_json)["value"],
            [],  # нет назначений в product_attributes
            json.loads(property_values_json)["value"],
        )
        attr = next(a for a in result["attributes"] if a["guid"] == ATTR_GUID)
        assert attr["source"] == "property_values"
        assert attr["numeric_candidate"] is True
        assert attr["numeric_unit"] == "мм²"
        numbers = {e["number"] for e in attr["numeric_examples"]}
        assert numbers == {10.0, 16.0}

    def test_classify_value_type(self):
        assert (
            ofa.classify_value_type({"Types": ["CatalogRef.ЗначенияСвойствОбъектов"]})
            == "enum"
        )
        assert ofa.classify_value_type({"Types": ["Number"]}) == "number"
        assert ofa.classify_value_type({"Types": ["String"]}) == "string"
        assert ofa.classify_value_type({"Types": ["Boolean"]}) == "bool"
        assert ofa.classify_value_type(None) == "unknown"


# ─── cross_reference_report (D-08) ───────────────────────────────────────────


class TestCrossReferences:
    def test_null_guid_is_null_not_broken(self, products_json):
        entities = {"products": json.loads(products_json)["value"]}
        report = ofa.cross_reference_report(entities)
        # Parent_Key = NULL_GUID не должен считаться битой ссылкой
        assert report["links"] == {}

    def test_broken_reference_detected(self, products_json, property_values_json):
        records = json.loads(products_json)["value"]
        records[0]["Parent_Key"] = BROKEN_GUID
        entities = {
            "products": records,
            "property_values": json.loads(property_values_json)["value"],
        }
        report = ofa.cross_reference_report(entities)
        link = report["links"]["products.Parent_Key"]
        assert link["broken"] == 1
        assert link["broken_examples"] == [BROKEN_GUID]
        # Owner_Key в property_values ссылается на ATTR_GUID, которого нет во вселенной
        assert report["links"]["property_values.Owner_Key"]["broken"] == 2


# ─── Полный проход analyze_items + build_stats ───────────────────────────────


class TestAnalyzeItems:
    def test_full_pass(
        self,
        products_json,
        attribute_defs_json,
        product_attributes_json,
        property_values_json,
    ):
        items = [
            ("products.json", products_json),
            ("attributes_def.json", attribute_defs_json),
            ("product_attributes.json", product_attributes_json),
            ("property_values.json", property_values_json),
            ("import.xml", CML_IMPORT),
        ]
        result = ofa.analyze_items(items, source="test")
        assert set(result.entities) == {
            "products",
            "attribute_defs",
            "product_attributes",
            "property_values",
        }
        assert result.commerceml[0]["role"] == "import"
        stats = ofa.build_stats(result)
        assert stats["attributes"]["total_assignments"] == 2
        assert stats["entities"]["products"]["active"] == 1

    def test_unknown_entity_goes_other(self):
        data = make_odata("Catalog_НечтоНеведомое", [{"Ref_Key": "x"}])
        result = ofa.analyze_items([("x.json", data)], source="test")
        assert "other" in result.entities

    def test_stock_summary_min_row_balance(self):
        data = make_odata(
            "Collection(StandardODATA.AccumulationRegister_ЗапасыНаСкладах_Balance)",
            [
                {"Номенклатура_Key": PRODUCT_GUID, "КоличествоBalance": 10},
                {"Номенклатура_Key": PRODUCT_GUID, "КоличествоBalance": -4},
            ],
        )
        result = ofa.analyze_items([("stock.json", data)], source="test")
        stats = ofa.build_stats(result)
        summary = stats["stock_summary"]
        assert summary["negative_rows"] == 1
        assert summary["min_row_balance"] == -4
        assert summary["min_balance"] == 6

    def test_odata_error_recorded(self):
        data = json.dumps({"odata.error": {"code": "8", "message": {}}}).encode()
        result = ofa.analyze_items([("err.json", data)], source="test")
        assert result.errors and result.errors[0]["file"] == "err.json"

    def test_single_element_form(self):
        doc = {
            "odata.metadata": METADATA_BASE
            + "Catalog_НоменклатураПрисоединенныеФайлы/@Element",
            "Ref_Key": "21902754-0e0b-11f0-816f-00155d0a290e",
        }
        result = ofa.analyze_items(
            [("file.json", json.dumps(doc).encode())], source="test"
        )
        assert result.files[0]["records"] == 1
        assert result.files[0]["bucket"] == "other"


# ─── MinIO-итератор с моком aiobotocore ──────────────────────────────────────


class TestMinioIterator:
    def test_iter_minio_objects_with_mock(self, monkeypatch):
        class FakeBody:
            def __init__(self, payload: bytes):
                self._payload = payload

            async def read(self):
                return self._payload

        class FakeClient:
            def __init__(self, payload: bytes):
                self._payload = payload

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def list_objects_v2(self, **kwargs):
                return {
                    "Contents": [{"Key": "a/products.json"}, {"Key": "b/"}],
                    "IsTruncated": False,
                }

            async def get_object(self, Bucket, Key):
                return {"Body": FakeBody(self._payload)}

        payload = '{"odata.metadata": "m#Catalog_ВидыЦен", "value": []}'.encode()
        client = FakeClient(payload)

        class FakeSession:
            def create_client(self, *args, **kwargs):
                return client

        import types

        fake_module = types.ModuleType("aiobotocore.session")
        fake_module.get_session = lambda: FakeSession()
        monkeypatch.setitem(sys.modules, "aiobotocore", types.ModuleType("aiobotocore"))
        monkeypatch.setitem(sys.modules, "aiobotocore.session", fake_module)

        items = ofa.iter_minio_objects(
            bucket="onec-intake",
            prefix="a/",
            endpoint="localhost:9000",
            access_key="k",
            secret_key="s",
            secure=False,
        )
        # каталоги (key на /) пропускаются
        assert items == [("a/products.json", payload)]


# ─── CLI end-to-end ──────────────────────────────────────────────────────────


class TestCli:
    def test_cli_end_to_end(self, tmp_path, products_json):
        src = tmp_path / "src"
        src.mkdir()
        (src / "products.json").write_bytes(products_json)
        (src / "import.xml").write_bytes(CML_IMPORT)
        report_dir = tmp_path / "reports"
        code = ofa.main(
            [
                "--path",
                str(src),
                "--glob",
                "*",
                "--report-dir",
                str(report_dir),
                "--label",
                "test",
            ]
        )
        assert code == 0
        md_files = list(report_dir.glob("*_test.md"))
        json_files = list(report_dir.glob("*_test.json"))
        assert len(md_files) == 1
        assert len(json_files) == 1
        md = md_files[0].read_text(encoding="utf-8")
        assert "Catalog_Номенклатура" in md
        report = json.loads(json_files[0].read_text(encoding="utf-8"))
        assert report["stats"]["entities"]["products"]["active"] == 1

    def test_cli_missing_path(self):
        code = ofa.main(["--path", "/nonexistent/dir"])
        assert code == 1

    def test_cli_minio_requires_keys(self, monkeypatch):
        monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
        monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
        code = ofa.main(["--minio", "--bucket", "onec-intake"])
        assert code == 1
