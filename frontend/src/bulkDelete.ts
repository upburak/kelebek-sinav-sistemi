import { notify } from './notify'

/**
 * Toplu silme (Karar 73): önce neyin silineceğini sayılarıyla sorar, onaylanırsa siler.
 * Uygulama silmeden önce kendiliğinden güvenlik yedeği alır.
 */
export type BulkScope = 'exams' | 'students' | 'classrooms'

const QUESTIONS: Record<BulkScope, (counts: Record<string, number>) => string> = {
  exams: (counts) => `Bu eğitim yılındaki ${counts.exams} sınavın tamamı; dağıtımları ve raporlarıyla birlikte silinecek.`,
  students: (counts) => `Bu eğitim yılındaki ${counts.students} öğrencinin tamamı silinecek.${counts.exams ? ` Öğrenciler sınavlara bağlı olduğu için ${counts.exams} sınav da silinecek.` : ''}`,
  classrooms: (counts) => `${counts.classrooms} derslik, oturma planlarıyla birlikte silinecek.${counts.exams ? ` Planlar sınavlara bağlı olduğu için ${counts.exams} sınav da silinecek.` : ''}`,
}

const RESULTS: Record<BulkScope, (deleted: Record<string, number>) => string> = {
  exams: (deleted) => `${deleted.exams} sınav silindi.`,
  students: (deleted) => `${deleted.students} öğrenci silindi${deleted.exams ? `, ${deleted.exams} sınavla birlikte` : ''}.`,
  classrooms: (deleted) => `${deleted.classrooms} derslik silindi${deleted.exams ? `, ${deleted.exams} sınavla birlikte` : ''}.`,
}

/** Silme yapıldıysa true döner; vazgeçildiyse ya da hata olduysa false. */
export async function bulkDelete(scope: BulkScope, academicYearId: string): Promise<boolean> {
  try {
    const previewResponse = await fetch(`/api/bulk-delete/preview?scope=${scope}&academic_year_id=${encodeURIComponent(academicYearId)}`)
    const preview = await previewResponse.json()
    if (!previewResponse.ok) throw new Error(preview.error ?? 'Silinecek kayıtlar sayılamadı.')
    const question = `${QUESTIONS[scope](preview.counts as Record<string, number>)}\n\nSilmeden önce verilerin yedeği alınır; yanlışlıkla silersen Yedek ve arşiv bölümünden geri yükleyebilirsin.\n\nSilinsin mi?`
    if (!window.confirm(question)) return false
    const response = await fetch('/api/bulk-delete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, academic_year_id: academicYearId, confirm: true }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error ?? 'Silme yapılamadı.')
    notify.success(`${RESULTS[scope](data.deleted as Record<string, number>)} Öncesinde yedek alındı: ${data.safety_backup}.`)
    return true
  } catch (reason) {
    notify.error(reason instanceof Error ? reason.message : 'Silme yapılamadı. Sayfayı yenileyip tekrar deneyin.')
    return false
  }
}
