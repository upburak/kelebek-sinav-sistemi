#!/usr/bin/env bash
# Çalışma klasörünün anlık görüntüsünü ayrı bir yedek dalına gönderir.
#
# Bu betik SİZİN çalışmanıza dokunmaz: dalınızı değiştirmez, HEAD'i oynatmaz,
# index'inizi ve çalışma dizininizi ellemez. Geçici bir index'te ağaç nesnesi
# oluşturup commit'i doğrudan yedek dalına gönderir. Yani siz düzenleme
# yaparken arka planda çalışsa bile yarım işiniz kendi dalınıza commit'lenmez.
#
# Kullanım:
#   ./scripts/auto-push.sh            # anlık görüntü al ve gönder
#   ./scripts/auto-push.sh --dry-run  # ne yapacağını göster, gönderme
#
# Ayarlar (ortam değişkeni):
#   KELEBEK_AUTOPUSH_BRANCH  hedef dal (varsayılan: otomatik-yedek/<bilgisayar adı>)
#   KELEBEK_AUTOPUSH_REMOTE  uzak depo adı (varsayılan: origin)

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

REMOTE="${KELEBEK_AUTOPUSH_REMOTE:-origin}"
BRANCH="${KELEBEK_AUTOPUSH_BRANCH:-otomatik-yedek/$(hostname -s 2>/dev/null || echo mac)}"
LAST_REF="refs/kelebek/autopush"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "DURDU: $*"; exit 1; }

# Depoya ait olmayan veya yarım kalmış durumlarda hiç karışma.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Burası bir git deposu değil: $ROOT"
GIT_DIR="$(git rev-parse --git-dir)"
for marker in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD BISECT_LOG; do
  [ -e "$GIT_DIR/$marker" ] && die "Devam eden bir git işlemi var ($marker); anlık görüntü alınmadı."
done
[ -d "$GIT_DIR/rebase-merge" ] || [ -d "$GIT_DIR/rebase-apply" ] && die "Devam eden rebase var; anlık görüntü alınmadı."
git remote get-url "$REMOTE" >/dev/null 2>&1 || die "Uzak depo bulunamadı: $REMOTE"

# Anlık görüntü geçici bir index'te hazırlanır; sizin index'iniz değişmez.
# mktemp -t davranışı macOS ile Linux arasında farklı; şablonu tam veriyoruz.
TEMP_INDEX="$(mktemp "${TMPDIR:-/tmp}/kelebek-autopush-index.XXXXXX")"
trap 'rm -f "$TEMP_INDEX"' EXIT
export GIT_INDEX_FILE="$TEMP_INDEX"

git read-tree HEAD 2>/dev/null || git read-tree --empty
git add -A || die "Dosyalar anlık görüntüye alınamadı."

# .gitignore'a ek güvenlik ağı: gerçek öğrenci verisi, veritabanı, yedek ve
# gizli anahtar dosyaları hiçbir koşulda gönderilmez (AGENTS.md veri güvenliği).
# Yalnızca değişenler değil, anlık görüntünün TAMAMI taranır: asıl tehlike
# daha önce yanlışlıkla izlenmeye başlamış ve .gitignore'un artık eleyemediği
# bir dosyadır. KELEBEK_AUTOPUSH_SKIP_SCAN=1 ile kapatılabilir.
if [ "${KELEBEK_AUTOPUSH_SKIP_SCAN:-0}" = "1" ]; then
  RISKY=""
else
  RISKY="$(git ls-files --cached 2>/dev/null | grep -Ei \
    '\.(sqlite|sqlite3|db|db-wal|db-shm|pem|key|p12|pfx)$|\.(xlsx|xls|csv)$|(^|/)(instance|backups?|exports)/' \
    | grep -v '^frontend/public/downloads/' || true)"
fi
if [ -n "$RISKY" ]; then
  log "DURDU: gönderilmemesi gereken dosyalar var. .gitignore'u kontrol edin:"
  printf '  %s\n' $RISKY
  exit 1
fi

TREE="$(git write-tree)" || die "Ağaç nesnesi yazılamadı."

# Üst commit: varsa önceki anlık görüntü, yoksa bulunduğunuz commit.
if PARENT="$(git rev-parse --verify -q "$LAST_REF")"; then
  PREVIOUS_TREE="$(git rev-parse -q --verify "$LAST_REF^{tree}" || true)"
  if [ "$TREE" = "$PREVIOUS_TREE" ]; then
    log "Değişiklik yok; gönderim yapılmadı."
    exit 0
  fi
else
  PARENT="$(git rev-parse HEAD 2>/dev/null)" || die "HEAD okunamadı (depo boş olabilir)."
fi

CHANGED="$(git diff --name-only "$PARENT" --cached 2>/dev/null | wc -l | tr -d ' ')"
BRANCH_NOW="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
MESSAGE="Otomatik anlık görüntü $(date '+%Y-%m-%d %H:%M') · dal: ${BRANCH_NOW} · ${CHANGED} dosya"

if [ "$DRY_RUN" = 1 ]; then
  log "[deneme] gönderilecekti: $MESSAGE -> $REMOTE/$BRANCH"
  exit 0
fi

COMMIT="$(git commit-tree "$TREE" -p "$PARENT" -m "$MESSAGE")" || die "Commit oluşturulamadı."
if git push -q "$REMOTE" "$COMMIT:refs/heads/$BRANCH" 2>/dev/null; then
  git update-ref "$LAST_REF" "$COMMIT"
  log "Gönderildi: $REMOTE/$BRANCH ($CHANGED dosya, ${COMMIT:0:7})"
else
  log "Gönderilemedi (ağ veya yetki). Bir sonraki denemede yeniden gönderilecek."
  exit 1
fi
