# Sade Arayüz (0.7.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcının gördüğü kavramları azaltmak: derslik doğrudan kendi planını açar, her sınavın kendi sayfası olur, her işlemin sonucu aynı yerde bildirilir.

**Architecture:** Veritabanı şeması değişmez. Arka uçta plan düzenleme "kesinleşmiş sınavda kullanılıyorsa kopyala, değilse yerinde kaydet" kuralına geçer ve taslak sınavlar dersliğin aktif planına yeniden bağlanır. Ön yüzde iki büyük dosya (`ExamOrganizer.tsx`, `ClassroomManager.tsx`) tek amaçlı bileşenlere ayrılır; ortak bir bildirim modülü eklenir.

**Tech Stack:** Flask 3, SQLAlchemy 2, SQLite · React 19, TypeScript, Vite · testler: `unittest` (backend/tests), `pytest` + Playwright (tests/e2e).

**Spec:** `docs/superpowers/specs/2026-11-11-sade-arayuz-design.md`

## Global Constraints

- Veritabanı şeması değişmez; migration eklenmez.
- Karar belgesi `docs/Kelebek_Sinav_Sistemi_Ana_Proje_Karar_Dokumani_v4.3.md` değiştirilmez.
- Testlerde yalnızca sentetik veri kullanılır; gerçek öğrenci verisi, veritabanı, yedek depoya girmez.
- macOS ve Windows desteği korunur: dosya tutamaçları kapatılır (`contextlib.closing`), yol ayırıcı varsayılmaz.
- Normal görünümde şu kelimeler geçmez: "sürüm", "şablon", "aday", "sabitle". Yalnızca "İleri düzey" bölümlerinde geçebilir.
- Arayüz metni Türkçedir; düğme adları fiille başlar ("Planı düzenle", "Dağıtımı başlat").
- Mevcut `data-testid` değerleri korunur: `exam-new-btn`, `exam-create-submit`, `exam-notice`, `candidate-create-*`, `candidate-result-*`, `final-review-open-*`, `finalize-confirm-checkbox`, `finalize-submit-btn`, `exam-reports-*`, `exam-guide-title-*`, `dashboard`, `student-search`.
- Yayım tek sürümde yapılır: 0.7.0. Ara görevler `main`'e birleştirilmez.
- Commit yazarı: `-c user.email=41228441+upburak@users.noreply.github.com -c user.name=upburak`.
- Her görevin sonunda: `ruff check backend tests`, `npm --prefix frontend run build`, ilgili testler.

Test komutları (depo kökünden):

```bash
# birim (tek modül)
KELEBEK_DATA_DIR=$(mktemp -d) PYTHONPATH=backend:backend/tests .venv/bin/python -m unittest <modül> -v
# birim (hepsi)
KELEBEK_DATA_DIR=$(mktemp -d) PYTHONPATH=backend:backend/tests .venv/bin/python -m unittest discover -s backend/tests
# uçtan uca (arayüz derlenmiş olmalı)
npm --prefix frontend run build && KELEBEK_CHROMIUM=/opt/pw-browsers/chromium .venv/bin/python -m pytest tests/e2e -q
```

## Review Focus

1. **Aynı plan hem kesinleşmiş hem taslak sınavda kullanılırken düzenlenir** → kesinleşmiş sınavın koltukları ve krokisi değişmez, taslak sınav yeni plana bağlanır. (Görev 1)
2. **Plan değişikliği koltuk sayısını öğrenci sayısının altına düşürür** → taslak sınav "Derslikler" adımına döner ve eksik koltuk sayısını gösterir; dağıtım düğmesi görünmez. (Görev 3, Görev 6)
3. **Hiç planı olmayan ya da planı boş (0 koltuk) derslik açılır** → sayfa çökmez; "Bu dersliğin planı yok" durumu ve "Planı oluştur" düğmesi görünür. (Görev 2, Görev 5)
4. **Arşiv yılında plan düzenlenmeye çalışılır** → 403 döner, hiçbir kopya oluşmaz, taslak bağlantıları değişmez. (Görev 1, Görev 2)
5. **Art arda iki işlem bildirimi; biri hata** → hata bildirimi kullanıcı kapatana kadar kalır, sonraki başarı bildirimi onu silmez. (Görev 4)

---

### Task 1: Plan düzenleme kuralı (servis)

**Files:**
- Modify: `backend/kelebek/services/layouts.py`
- Modify: `backend/kelebek/api/classrooms.py:270-335` (`create_layout_version` gövdesindeki kopyalama `clone_layout`'a taşınır)
- Test: `backend/tests/test_layout_edit_rule.py`

**Interfaces:**
- Consumes: `activate_layout(session, layout)`, `layout_exam_count(session, layout_id)` (mevcut).
- Produces:
  - `clone_layout(session: Session, source: ClassroomLayout) -> ClassroomLayout` — aynı derslik/yıl/ad, `version = max+1`, masalar ve koltuklar kopyalanır; aktiflik değişmez.
  - `is_layout_frozen(session: Session, layout_id: str) -> bool` — plan `status == "completed"` ya da `archived_at` dolu bir sınavda kullanılıyorsa `True`.
  - `rebind_draft_exams(session: Session, old_layout: ClassroomLayout, new_layout: ClassroomLayout) -> int` — `old_layout`'u kullanan **taslak** sınavların `ExamOrganizationClassroom.layout_id` değerini `new_layout.id` yapar, o sınavların `selected_candidate_id` değerini `None` yapar, etkilenen sınav sayısını döndürür.
  - `prepare_layout_for_edit(session: Session, layout: ClassroomLayout) -> tuple[ClassroomLayout, int]` — dondurulmamışsa `(layout, 0)`; dondurulmuşsa kopyalar, kopyayı aktif yapar, taslakları kopyaya bağlar ve `(kopya, etkilenen_taslak_sayısı)` döndürür. Şablon (yılı olmayan) plan için `(layout, 0)`.
  - `LayoutReadOnlyError(ValueError)` — arşiv yılı planı için `prepare_layout_for_edit` bunu fırlatır.

- [ ] **Step 1: Düşen testleri yaz** (`test_exam_flow.ExamFlowTests` kurulumunu `test_layout_active_delete.py`'deki gibi yeniden kullan; yardımcılar `_classroom`, `_layout`, sınav oluşturma oradaki kalıpla)

```python
def test_unused_layout_is_edited_in_place(self):
    layout, moved = prepare_layout_for_edit(session, layout_obj)
    self.assertEqual((layout.id, moved), (original_id, 0))
    self.assertEqual(len(self._layouts(classroom_id)), 1)

def test_layout_of_a_finalized_exam_is_copied_and_copy_becomes_active(self):
    # sınav kesinleştirildikten sonra
    edited, moved = prepare_layout_for_edit(session, layout_obj)
    self.assertNotEqual(edited.id, original_id)
    self.assertTrue(edited.is_active)
    self.assertEqual(edited.version, 2)
    self.assertEqual(seat_count(edited.id), seat_count(original_id))

def test_finalized_exam_keeps_its_original_seats(self):
    before = self.client.get(f"/api/exam-organizations/{done_id}/distribution-candidates").get_json()
    prepare_layout_for_edit(session, layout_obj)
    after = self.client.get(f"/api/exam-organizations/{done_id}/distribution-candidates").get_json()
    self.assertEqual(before, after)

def test_draft_exam_follows_the_copy_and_loses_its_selection(self):  # Review Focus 1
    _edited, moved = prepare_layout_for_edit(session, layout_obj)
    self.assertEqual(moved, 1)
    draft = org(draft_id)
    self.assertEqual([r["layout_id"] for r in draft["room_selections"]], [_edited.id])
    self.assertIsNone(draft["selected_candidate_id"])

def test_archive_year_layout_cannot_be_prepared(self):  # Review Focus 4
    with self.assertRaises(LayoutReadOnlyError):
        prepare_layout_for_edit(session, archive_layout)
    self.assertEqual(layout_count_before, layout_count_after)

def test_template_is_edited_in_place(self):
    self.assertEqual(prepare_layout_for_edit(session, template)[0].id, template.id)
```

- [ ] **Step 2: Testlerin düştüğünü gör** — `unittest test_layout_edit_rule -v` → `ImportError: cannot import name 'prepare_layout_for_edit'`.
- [ ] **Step 3: Dört işlevi ve `LayoutReadOnlyError`'ı `services/layouts.py`'ye yaz.** Arşiv denetimi için `kelebek.db.current_academic_year_start()` kullan (`api/classrooms.py::_is_archive_layout` ile aynı kural).
- [ ] **Step 4: `create_layout_version` gövdesini `clone_layout` çağıracak şekilde sadeleştir**; uç davranışı değişmez (`test_layout_active_delete.test_new_version_inherits_active_state` geçmeye devam eder).
- [ ] **Step 5: Testleri geçir** — `unittest test_layout_edit_rule test_layout_active_delete -v` → OK.
- [ ] **Step 6: Commit** — `git commit -m "Plan düzenleme kuralı: kesinleşmişse kopyala, değilse yerinde"`.

### Task 2: Düzenleme uçları ve derslik planı ucu

**Files:**
- Modify: `backend/kelebek/api/classrooms.py` (`move_layout_desk`, `set_layout_seat_availability`, `generate_classroom_layout`, yeni `get_classroom_plan`)
- Test: `backend/tests/test_classroom_plan_api.py`

**Interfaces:**
- Consumes: `prepare_layout_for_edit`, `LayoutReadOnlyError` (Görev 1).
- Produces:
  - `GET /api/classrooms/<classroom_id>/plan?academic_year_id=<id>` → `200 {"classroom": {"id","name"}, "plan": <_layout_detail çıktısı + "is_active","exam_count","finalized_exam_count"> | null, "other_layout_count": int}`. Aktif plan yoksa `"plan": null`.
  - Üç düzenleme ucu artık "son sürüm" şartı aramaz; `prepare_layout_for_edit` çağırır. Yanıtlarına şu alanlar eklenir: `"layout_id": str` (kopyalandıysa yeni kimlik), `"copied": bool`, `"affected_draft_exam_count": int`. Masa/koltuk kimliği kopyada değiştiği için kopyalama olduğunda istek kopyadaki karşılık gelen masaya/koltuğa uygulanır (eşleştirme: masa `label`, koltuk `seat_number`).
  - `generate_classroom_layout`: plan dondurulmuşsa kopya **boş** oluşturulmaz; mevcut kural korunur (masası olan planda 409). Boş planda çalışır.

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_plan_endpoint_returns_the_active_plan_with_usage(self):
    data = self.client.get(f"/api/classrooms/{cid}/plan?academic_year_id={self.year_id}").get_json()
    self.assertEqual(data["plan"]["id"], active_id)
    self.assertEqual((data["plan"]["exam_count"], data["plan"]["finalized_exam_count"]), (1, 0))
    self.assertEqual(data["other_layout_count"], 1)

def test_classroom_without_any_plan_returns_null_plan(self):  # Review Focus 3
    data = self.client.get(f"/api/classrooms/{empty_cid}/plan?academic_year_id={self.year_id}")
    self.assertEqual((data.status_code, data.get_json()["plan"]), (200, None))

def test_seat_toggle_on_unused_plan_edits_in_place(self):
    r = self.client.patch(f".../seats/{seat_id}", json={"is_available": False, "reason": "kırık"})
    self.assertEqual((r.get_json()["copied"], r.get_json()["layout_id"]), (False, layout_id))

def test_seat_toggle_on_finalized_plan_edits_the_copy(self):
    r = self.client.patch(f".../seats/{seat_id}", json={"is_available": False, "reason": "kırık"}).get_json()
    self.assertTrue(r["copied"]); self.assertNotEqual(r["layout_id"], layout_id)
    self.assertTrue(original_seat_still_available(seat_id))
    self.assertFalse(seat_in_copy_with_same_number_is_available(r["layout_id"]))

def test_desk_move_reports_affected_draft_exams(self):
    r = self.client.patch(f".../desks/{desk_id}", json={"x": 6.0, "y": 0.0}).get_json()
    self.assertEqual(r["affected_draft_exam_count"], 1)

def test_archive_year_edit_is_refused_without_side_effects(self):  # Review Focus 4
    r = self.client.patch(f".../seats/{seat_id}", json={"is_available": False})
    self.assertEqual(r.status_code, 403)
```

- [ ] **Step 2: Düştüğünü gör** — `unittest test_classroom_plan_api -v` → 404 / `KeyError: 'copied'`.
- [ ] **Step 3: `get_classroom_plan` ucunu ekle**; `academic_year_id` yoksa 400.
- [ ] **Step 4: Üç düzenleme ucunu `prepare_layout_for_edit` üzerinden çalıştır**; `LayoutReadOnlyError` → 403 "Arşiv yılı düzenleri salt okunur."
- [ ] **Step 5: Testleri geçir** — bu modül + `unittest discover` → OK.
- [ ] **Step 6: Commit** — `"Derslik planı ucu; düzenleme uçları kopyala/yerinde kuralını kullanır"`.

### Task 3: Sınav yanıtı ve aktif plan izleme

**Files:**
- Modify: `backend/kelebek/services/exam_organizer.py` (`list_organizations`, yeni `distribution_fingerprint`)
- Modify: `backend/kelebek/api/exam_organizations.py:104` (`_distribution_fingerprint` servise taşınır; eski ad içe aktarılan takma ad olarak kalır)
- Modify: `backend/kelebek/api/classrooms.py::activate_classroom_layout` (taslakları yeni aktif plana bağlar)
- Test: `backend/tests/test_exam_plan_follow.py`

**Interfaces:**
- Consumes: `rebind_draft_exams` (Görev 1).
- Produces — her sınav nesnesine üç alan eklenir:
  - `"needs_redistribution": bool` — taslak sınavın en az bir `DistributionRun` kaydı var ama hiçbirinin `config_hash` değeri güncel parmak izine eşit değil.
  - `"group_count": int` — sınava giren farklı (sınıf, şube) sayısı.
  - `"stage": "rooms" | "distribute" | "review" | "done" | "archived"` — `archived_at` doluysa `archived`; `status == "completed"` ise `done`; derslik yok ya da `capacity_sufficient` yanlışsa `rooms`; `selected_candidate_id` yoksa `distribute`; aksi hâlde `review`.
  - `POST .../layouts/<id>/activate` yanıtına `"affected_draft_exam_count": int` eklenir.

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_stage_follows_the_exam_through_its_life(self):
    self.assertEqual(org()["stage"], "rooms")
    select_rooms(); self.assertEqual(org()["stage"], "distribute")
    distribute_and_select(); self.assertEqual(org()["stage"], "review")
    finalize(); self.assertEqual(org()["stage"], "done")

def test_plan_change_marks_the_draft_for_redistribution(self):
    distribute_and_select()
    toggle_a_seat_of_the_plan()
    self.assertTrue(org()["needs_redistribution"])
    self.assertEqual(candidates(), [])

def test_plan_shrinking_below_student_count_sends_exam_back_to_rooms(self):  # Review Focus 2
    close_seats_until_capacity_is(participants - 1)
    self.assertEqual((org()["stage"], org()["capacity_deficit"]), ("rooms", 1))

def test_activating_another_plan_moves_draft_exams_to_it(self):
    r = self.client.post(f".../layouts/{second_id}/activate").get_json()
    self.assertEqual(r["affected_draft_exam_count"], 1)
    self.assertEqual(org()["room_selections"][0]["layout_id"], second_id)

def test_group_count_counts_class_sections(self):
    self.assertEqual(org()["group_count"], len(selected_groups))
```

- [ ] **Step 2: Düştüğünü gör** — `KeyError: 'stage'`.
- [ ] **Step 3: `distribution_fingerprint`'i servise taşı, üç alanı `list_organizations` ve `create_organization` yanıtlarına ekle.**
- [ ] **Step 4: `activate_classroom_layout`'ta eski aktif plandan yenisine `rebind_draft_exams` çağır.**
- [ ] **Step 5: Testleri geçir** — bu modül + `unittest discover` + `pytest tests/e2e -q` → OK.
- [ ] **Step 6: Commit** — `"Sınav yanıtı: aşama, yeniden dağıtım gereği; taslaklar aktif planı izler"`.

### Task 4: Ortak sonuç bildirimi

**Files:**
- Create: `frontend/src/notify.tsx`
- Modify: `frontend/src/App.tsx` (kökte `<Notifications />`; liste aktarımı bitişinde bildirim)
- Modify: `frontend/src/styles.css`
- Test: `tests/e2e/test_notifications_ui_e2e.py`

**Interfaces:**
- Produces (`notify.tsx`):
  - `notify.success(message: string, action?: { label: string; onClick: () => void }): void` — 6 saniye sonra kendiliğinden kapanır.
  - `notify.error(message: string): void` — kullanıcı kapatana kadar kalır.
  - `<Notifications />` — sağ altta yığın; en fazla 4 bildirim, en yenisi altta. Kap: `data-testid="notifications"`, her öğe `data-testid="notification"` ve `data-kind="success" | "error"`, kapatma düğmesi `aria-label="Bildirimi kapat"`. Başarı `role="status"`, hata `role="alert"`.
  - Modül düzeyinde abone listesi tutar; React bağlamı gerekmez (her bileşen `import { notify } from './notify'`).

- [ ] **Step 1: Düşen testi yaz**

```python
def test_import_completion_is_announced_with_a_link_to_classrooms(page):
    # sentetik 48 öğrencilik dosyayı arayüzden içe aktar (test_student_import_ui_e2e kalıbı)
    note = page.get_by_test_id("notification").filter(has_text="öğrenci")
    expect(note).to_have_attribute("data-kind", "success")
    note.get_by_role("button", name="Derslik planlarını kontrol et").click()
    expect(page.locator("h1")).to_have_text("Derslikler")

def test_error_stays_until_closed_and_survives_a_later_success(page):  # Review Focus 5
    page.evaluate("window.__kelebekNotify.error('Deneme hatası')")
    page.evaluate("window.__kelebekNotify.success('Deneme başarısı')")
    page.wait_for_timeout(7000)
    expect(page.get_by_test_id("notification")).to_have_count(1)
    expect(page.get_by_test_id("notification")).to_have_attribute("data-kind", "error")
    page.get_by_label("Bildirimi kapat").click()
    expect(page.get_by_test_id("notification")).to_have_count(0)
```

(`window.__kelebekNotify = notify` yalnızca sınama kolaylığı için `notify.tsx` içinde atanır.)

- [ ] **Step 2: Düştüğünü gör** — `notification` bulunamaz.
- [ ] **Step 3: `notify.tsx`'i yaz ve `App.tsx` köküne `<Notifications />` ekle.**
- [ ] **Step 4: Liste aktarımı başarı yolunda `notify.success(`${n} öğrenci ve ${m} derslik hazır.`, { label: 'Derslik planlarını kontrol et', onClick: … })` çağır; aktarım hatasında `notify.error`.**
- [ ] **Step 5: Testleri geçir** — `pytest tests/e2e/test_notifications_ui_e2e.py -q` → 2 passed.
- [ ] **Step 6: Commit** — `"Ortak sonuç bildirimi"`.

### Task 5: Derslikler ekranı

**Files:**
- Create: `frontend/src/classrooms/ClassroomList.tsx`, `ClassroomPlan.tsx`, `PlanEditor.tsx`, `ClassroomAdvanced.tsx`, `types.ts`
- Modify: `frontend/src/ClassroomManager.tsx` (yalnızca bu dört bileşeni birleştiren ince kabuk kalır; dışa aktarım ve `Props` aynı)
- Modify: `frontend/src/styles.css`
- Test: `tests/e2e/test_classroom_plan_ui_e2e.py`

**Interfaces:**
- Consumes: `GET /api/classrooms/<id>/plan`, düzenleme uçlarının `copied` / `affected_draft_exam_count` alanları (Görev 2), `notify` (Görev 4).
- Produces:
  - `ClassroomList({ classrooms, selectedId, readOnly, onSelect, onChanged })` — kartlar; kart `data-testid="classroom-card-<id>"`.
  - `ClassroomPlan({ classroomId, academicYearId, readOnly, onChanged })` — durum satırı `data-testid="plan-status"` (örnek metin: "36 koltuk · 2 sınavda kullanılıyor"), ana düğme `data-testid="plan-edit-btn"` "Planı düzenle"; plan yoksa `data-testid="plan-empty"` ve "Planı oluştur" düğmesi.
  - `PlanEditor({ classroomId, plan, onSaved, onClose })` — mevcut masa sürükleme / koltuk kapatma / sütun kurma davranışı **değişmeden** taşınır; "Kopyala ve düzenle" adımı kalkar. Her kayıtta `notify.success`: kopyalandıysa "Plan kaydedildi. Kesinleşmiş sınavların krokisi değişmedi."; `affected_draft_exam_count > 0` ise sonuna "`N` taslak sınav yeni planı kullanacak." eklenir.
  - `ClassroomAdvanced({ classroomId, academicYearId, readOnly, onChanged })` — `<details data-testid="classroom-advanced">` özet metni "İleri düzey: ikinci plan, kopyalama, eski hâller"; içinde bugünkü düzen listesi (aktif yap, sil, şablon, yeni düzen).

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_classroom_card_opens_its_plan_directly(page):
    open_section(page, "Derslikler")
    page.locator("[data-testid^=classroom-card-]").first.click()
    expect(page.get_by_test_id("plan-status")).to_contain_text("koltuk")
    expect(page.get_by_test_id("plan-edit-btn")).to_have_text("Planı düzenle")

def test_normal_view_hides_internal_words(page):
    body = page.locator(".classroom-manager").inner_text().lower()
    advanced = page.get_by_test_id("classroom-advanced").inner_text().lower()
    visible = body.replace(advanced, "")
    assert not any(word in visible for word in ("sürüm", "şablon", "kopyala ve düzenle", "aktif yap"))

def test_classroom_without_a_plan_offers_to_create_one(page):  # Review Focus 3
    create_classroom_via_api("PLANSIZ SALON")
    open_classroom(page, "PLANSIZ SALON")
    expect(page.get_by_test_id("plan-empty")).to_be_visible()

def test_editing_a_plan_used_by_a_draft_exam_announces_the_effect(page):
    # API ile: sınav oluştur, bu dersliği seç
    open_classroom(page, room_name); page.get_by_test_id("plan-edit-btn").click()
    page.locator(".plan-seat").first.click()          # koltuğu kullanım dışı yap
    expect(page.get_by_test_id("notification")).to_contain_text("1 taslak sınav yeni planı kullanacak")
```

- [ ] **Step 2: Düştüğünü gör.**
- [ ] **Step 3: `types.ts` ve dört bileşeni yaz; `ClassroomManager.tsx`'i kabuğa indir.** Düzenleyici mantığı taşınırken davranış değiştirilmez; yalnızca sürüm açma adımı ve "son sürüm" salt-okunur uyarısı kaldırılır.
- [ ] **Step 4: Testleri geçir** — bu dosya + tüm `tests/e2e` → OK.
- [ ] **Step 5: Commit** — `"Derslikler: karta tıklayınca doğrudan plan; ileri düzey ayrı bölümde"`.

### Task 6: Sınav listesi ve sınav sayfası kabuğu

**Files:**
- Create: `frontend/src/exams/types.ts`, `api.ts`, `ExamList.tsx`, `ExamPage.tsx`, `ExamCreateForm.tsx`, `PeriodManager.tsx`, `steps/RoomsStep.tsx`, `steps/DistributeStep.tsx`
- Modify: `frontend/src/ExamOrganizer.tsx` (liste ↔ sayfa geçişini yöneten ince kabuk; dışa aktarım ve `Props` aynı)
- Test: `tests/e2e/test_exam_page_ui_e2e.py`; güncelle: `tests/e2e/test_exam_guided_flow_ui_e2e.py`

**Interfaces:**
- Consumes: sınav nesnesindeki `stage`, `needs_redistribution`, `group_count` (Görev 3); `notify` (Görev 4).
- Produces:
  - `api.ts`: `fetchJson<T>(url, init?) : Promise<T>` (hata gövdesindeki `error` metniyle `Error` fırlatır) ve sınav uçları için adlandırılmış işlevler: `listExams`, `createExam`, `saveRooms`, `createDistribution`, `listDistributions`, `selectDistribution`, `moveStudent`, `openFinalReview`, `finalizeExam`.
  - `ExamList({ exams, periods, readOnly, onOpen, onNew })` — satır `data-testid="exam-row-<id>"`; satırda durum `data-testid="exam-stage-<id>"` metni: `rooms`→"Derslik seçilecek", `distribute`→"Dağıtılacak", `review`→"Kontrol bekliyor", `done`→"Kesinleşti", `archived`→"Arşivde"; düğme `data-testid="exam-open-<id>"` "Aç". Dönem yönetimi listenin altında `data-testid="exam-period-manage-btn"`.
  - `ExamPage({ examId, readOnly, onBack, onReports })` — kök `data-testid="exam-card-<id>"` (mevcut testler için korunur), geri bağlantısı `data-testid="exam-back"` "← Sınavlara dön", şerit ve başlık bugünkü `exam-guide-*` kimlikleriyle. Şerit öğeleri düğmedir; tamamlanmış adım tıklanınca o adım gösterilir, ilerideki adım `disabled`.
  - `RoomsStep({ exam, roomOptions, readOnly, onSaved })`, `DistributeStep({ exam, readOnly, onDistributed })` — mevcut `exam-room-save-*`, `exam-room-select-all-*`, `candidate-create-*` kimlikleri korunur. `needs_redistribution` doğruysa `DistributeStep` başlığı "Derslik planı değişti, yeniden dağıt".
  - Yeni sınav oluşturulunca `ExamOrganizer` doğrudan o sınavın `ExamPage`'ini açar.

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_list_shows_one_row_per_exam_and_no_inline_controls(page):
    open_section(page, "Sınav organizasyonlar")
    row = page.locator("[data-testid^=exam-row-]").first
    expect(row.locator("button")).to_have_count(1)            # yalnızca "Aç"
    expect(page.locator(".exam-guide")).to_have_count(0)

def test_opening_an_exam_shows_only_that_exam(page):
    page.locator("[data-testid^=exam-open-]").first.click()
    expect(page.locator("[data-testid^=exam-card-]")).to_have_count(1)
    page.get_by_test_id("exam-back").click()
    expect(page.locator("[data-testid^=exam-row-]").first).to_be_visible()

def test_new_exam_opens_its_own_page(page):
    create_exam_via_form(page, "SAYFA AÇILIŞ SINAVI")
    expect(page.locator("[data-testid^=exam-guide-title-]")).to_have_text("Öğrencileri dersliklere dağıt")

def test_exam_short_of_seats_stays_on_rooms_step(page):  # Review Focus 2
    # API ile: tek derslik seç, kapasite < öğrenci
    open_exam(page, name)
    expect(page.locator("[data-testid^=exam-guide-title-]")).to_contain_text("koltuk eksik")
    expect(page.locator("[data-testid^=candidate-create-]")).to_have_count(0)

def test_plan_change_asks_for_redistribution(page):
    # API ile: dağıt, sonra planda bir koltuğu kapat (kapasite hâlâ yeterli)
    open_exam(page, name)
    expect(page.locator("[data-testid^=exam-guide-title-]")).to_have_text("Derslik planı değişti, yeniden dağıt")
```

`test_exam_guided_flow_ui_e2e.py` içindeki iki test, sınav oluşturduktan sonra kartı listede aramak yerine açılan sayfada arayacak şekilde güncellenir; doğrulamaları değişmez.

- [ ] **Step 2: Düştüğünü gör.**
- [ ] **Step 3: `types.ts`, `api.ts`, `ExamList`, `ExamCreateForm`, `PeriodManager`'ı `ExamOrganizer.tsx`'ten taşıyarak yaz.** Otomatik derslik seçimi (0.6.1 kuralı: yalnızca sınava giren sınıfların derslikleri) `ExamCreateForm`'da aynen kalır.
- [ ] **Step 4: `ExamPage`, `RoomsStep`, `DistributeStep`'i yaz; `ExamOrganizer.tsx`'i kabuğa indir.** Bu görevde Kontrol/Kesinleştirme/Raporlar adımları için mevcut JSX geçici olarak `ExamPage` içinde kalır (Görev 7–8 taşır).
- [ ] **Step 5: Testleri geçir** — tüm `tests/e2e` → OK.
- [ ] **Step 6: Commit** — `"Sınavlar: yalın liste ve her sınavın kendi sayfası"`.

### Task 7: Kontrol ve kesinleştirme adımları

**Files:**
- Create: `frontend/src/exams/SeatingPlan.tsx`, `steps/ReviewStep.tsx`, `steps/FinalizeStep.tsx`
- Modify: `frontend/src/exams/ExamPage.tsx`
- Test: `tests/e2e/test_exam_review_ui_e2e.py`

**Interfaces:**
- Consumes: `api.ts` (Görev 6), `notify`.
- Produces:
  - `SeatingPlan({ plan, violations, selectedParticipantId, editable, busy, onSeatClick })` — veri prop ile gelir, kendi isteği yoktur. Derslik sekmeleri `data-testid="plan-room-tab-<layout_id>"`, sınıf sırasına göre; bir seferde tek derslik (`.candidate-plan-room` sayısı 1).
  - `ReviewStep({ exam, distributions, readOnly, onChanged, onFinalize })` — yalnızca geçerli dağıtımı gösterir; sonuç satırı `candidate-result-<id>`. "Yeniden dağıt" `candidate-recreate-<examId>`. Birden fazla dağıtım varsa tek düğme `data-testid="distribution-back-<examId>"` "Önceki dağıtıma dön" (bir önceki dağıtımı seçer); liste gösterilmez. Yer değiştirme sonrası `notify.success("<Ad Soyad> <derslik> K<no> koltuğuna taşındı.")`.
  - `FinalizeStep({ exam, review, readOnly, onDone, onBack })` — `finalize-confirm-checkbox`, `finalize-submit-btn` korunur; başarıda `notify.success("«<ad>» kesinleşti. Raporlar hazır.")`.

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_review_shows_one_room_at_a_time_and_swaps_two_students(page):
    open_exam_in_review(page)
    expect(page.locator(".candidate-plan-room")).to_have_count(1)
    seats = page.locator("button.candidate-plan-seat.occupied")
    first, second = seats.nth(0).get_attribute("aria-label"), seats.nth(1).get_attribute("aria-label")
    seats.nth(0).click(); seats.nth(1).click()
    expect(page.get_by_test_id("notification")).to_contain_text("koltuğuna taşındı")
    assert seats.nth(0).get_attribute("aria-label").split(":")[1] == second.split(":")[1]

def test_previous_distribution_is_one_button_not_a_list(page):
    page.locator("[data-testid^=candidate-recreate-]").click()
    back = page.locator("[data-testid^=distribution-back-]")
    expect(back).to_have_text("Önceki dağıtıma dön")
    expect(page.locator(".exam-previous")).to_have_count(0)
    back.click()
    expect(page.locator("[data-testid^=candidate-result-]")).to_be_visible()

def test_word_aday_does_not_appear_on_the_exam_page(page):
    assert "aday" not in page.locator("[data-testid^=exam-card-]").inner_text().lower()

def test_finalize_announces_and_moves_to_reports(page):
    page.locator("[data-testid^=final-review-open-]").click()
    page.get_by_test_id("finalize-confirm-checkbox").check(); page.get_by_test_id("finalize-submit-btn").click()
    expect(page.get_by_test_id("notification")).to_contain_text("kesinleşti")
    expect(page.locator("[data-testid^=exam-guide-title-]")).to_have_text("Sınav kesinleşti")
```

- [ ] **Step 2: Düştüğünü gör.**
- [ ] **Step 3: Üç bileşeni mevcut JSX'ten taşıyarak yaz; `ExamPage`'e bağla.** İhlal listesi, "Tümünü düzelt", ihlalli koltuğa odaklanınca sekme değiştirme davranışı korunur.
- [ ] **Step 4: Testleri geçir** — tüm `tests/e2e` → OK.
- [ ] **Step 5: Commit** — `"Sınav sayfası: kontrol ve kesinleştirme adımları"`.

### Task 8: Raporlar adımı ve ileri düzey

**Files:**
- Create: `frontend/src/exams/steps/ReportsStep.tsx`, `frontend/src/exams/ExamAdvanced.tsx`
- Modify: `frontend/src/ReportCenter.tsx` (isteğe bağlı `organizationId` prop'u: verilirse sınav seçici gizlenir ve o sınav yüklenir)
- Modify: `frontend/src/exams/ExamPage.tsx`, `frontend/src/ExamLifecyclePanel.tsx` (yalnızca `ExamAdvanced` içinden kullanılır)
- Test: `tests/e2e/test_exam_reports_advanced_ui_e2e.py`

**Interfaces:**
- Consumes: `ReportCenter` (mevcut), `ExamLifecyclePanel` (mevcut), `notify`.
- Produces:
  - `ReportsStep({ exam })` — `<ReportCenter organizationId={exam.id} />` sarar; kök `data-testid="exam-reports-step"`. Menüdeki "Raporlar" bölümü aynı `ReportCenter`'ı `organizationId` olmadan kullanmaya devam eder.
  - `ExamAdvanced({ exam, periods, readOnly, onChanged })` — `<details data-testid="exam-advanced-<id>">`; özet: taslakta "İleri düzey: kurallar, derslik sabitleme, dönem, plan seçimi", kesinleşmişte "İleri düzey: arşivle, kopyala, öğrenci listesini karşılaştır". İçerik: oturma kuralları, derslik sabitleyerek yeniden dağıtma, dönem değiştirme, sınava özel plan seçimi (derslik başına plan `<select>`), karşılaştırma, kopyalama, arşivleme.
  - Sınav listesinde PDF düğmesi yoktur.

- [ ] **Step 1: Düşen testleri yaz**

```python
def test_reports_are_the_last_step_of_the_exam_page(page):
    open_finalized_exam(page)
    expect(page.get_by_test_id("exam-reports-step")).to_be_visible()
    expect(page.get_by_test_id("exam-reports-step").get_by_text("Derslik kapı krokisi")).to_be_visible()
    expect(page.get_by_test_id("exam-reports-step").locator("select").filter(has_text="YAZILI")).to_have_count(0)

def test_reports_menu_still_lists_all_finalized_exams(page):
    open_section(page, "Raporlar")
    expect(page.get_by_text("Raporlanacak sınav")).to_be_visible()

def test_list_rows_have_no_pdf_buttons(page):
    open_section(page, "Sınav organizasyonlar")
    assert "PDF" not in page.locator("[data-testid^=exam-row-]").first.inner_text()

def test_archive_lives_under_advanced(page):
    open_finalized_exam(page)
    expect(page.locator("[data-testid^=archive-btn-]")).not_to_be_visible()
    page.locator("[data-testid^=exam-advanced-] > summary").click()
    expect(page.locator("[data-testid^=archive-btn-]")).to_be_visible()
```

- [ ] **Step 2: Düştüğünü gör.**
- [ ] **Step 3: `ReportCenter`'a `organizationId` prop'unu ekle; `ReportsStep` ve `ExamAdvanced`'i yaz; `ExamPage`'de kalan geçici JSX'i kaldır.**
- [ ] **Step 4: `ExamOrganizer.tsx`'te ölü kod kalmadığını doğrula** — `wc -l frontend/src/ExamOrganizer.tsx` 150 satırın altında; `npm --prefix frontend run build` uyarısız.
- [ ] **Step 5: Testleri geçir** — tüm `tests/e2e` + `unittest discover` → OK.
- [ ] **Step 6: Commit** — `"Sınav sayfası: raporlar adımı ve ileri düzey bölümü"`.

### Task 9: Bildirimlerin yaygınlaştırılması, sürüm ve belgeler

**Files:**
- Modify: `frontend/src/classrooms/*.tsx`, `frontend/src/exams/**/*.tsx`, `frontend/src/BackupManager.tsx`, `frontend/src/App.tsx` (kalan yerel başarı/hata iletileri `notify`'a taşınır; satır içi doğrulama iletileri yerinde kalır)
- Modify: `backend/kelebek/version.py`, `pyproject.toml` → `0.7.0`; `backend/kelebek/release_notes.py`; `CHANGELOG.md`; `docs/DEVAM_DURUMU_2026-11-09.md`
- Test: `tests/e2e/test_notifications_ui_e2e.py` (ekleme)

**Interfaces:**
- Consumes: `notify` (Görev 4).
- Produces: sürüm 0.7.0; `exam-notice` kimliği, sınav oluşturma bildiriminde `notification` öğesine de verilir (mevcut testler için).

- [ ] **Step 1: Düşen testi yaz**

```python
@pytest.mark.parametrize("action, text", [
    (save_room_selection, "Derslik seçimi kaydedildi"),
    (rename_classroom, "adı değiştirildi"),
    (create_backup, "Yedek"),
    (save_school_profile, "Okul bilgileri kaydedildi"),
])
def test_every_save_is_announced_in_the_same_place(page, action, text):
    action(page)
    expect(page.get_by_test_id("notifications").get_by_test_id("notification").last).to_contain_text(text)
```

- [ ] **Step 2: Düştüğünü gör.**
- [ ] **Step 3: Dört işlemi ve taşınan diğer iletileri `notify`'a bağla; süren işlerde düğme metni "…iyor…" durumunu gösterir ve `disabled` olur.**
- [ ] **Step 4: Sürümü 0.7.0 yap; sürüm notu (üç madde: derslik doğrudan planını açar, her sınavın kendi sayfası, her işlemin sonucu bildirilir), CHANGELOG ve devam notunu yaz.**
- [ ] **Step 5: Tam doğrulama** — `ruff check backend tests` temiz; `unittest discover` OK; `pytest tests/e2e -q` iki kez üst üste OK; `npm --prefix frontend run build` başarılı.
- [ ] **Step 6: Görsel kontrol** — 236 öğrencilik sentetik veriyle (`scratchpad/veri/liste.xlsx`; depoya eklenmez) Derslikler, sınav listesi ve sınav sayfasının her adımının ekran görüntüsü alınır ve kullanıcıya gönderilir.
- [ ] **Step 7: Commit, PR, CI yeşilse birleştir; v0.7.0 paketlerini doğrula ve indirme bağlantılarını ver.**
