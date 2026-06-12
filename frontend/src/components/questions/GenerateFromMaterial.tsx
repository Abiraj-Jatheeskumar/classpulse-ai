import { useState } from 'react';
import { X, Upload, Sparkles, Trash2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/Button';
import {
  materialQuestionService,
  GeneratedQuestion,
  GenerationMode,
} from '../../services/materialQuestionService';

interface Props {
  courseId?: string;
  sessionId?: string;
  onClose: () => void;
  onSaved: () => void; // called after questions are saved (parent reloads bank)
}

const clusterColors: Record<string, string> = {
  passive: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  moderate: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  active: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
};

export const GenerateFromMaterial = ({ courseId, sessionId, onClose, onSaved }: Props) => {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<GenerationMode>('difficulty');
  const [fixedCluster, setFixedCluster] = useState<'passive' | 'moderate' | 'active'>('passive');
  const [countPerUnit, setCountPerUnit] = useState(1);
  const [topic, setTopic] = useState('');

  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [preview, setPreview] = useState<GeneratedQuestion[] | null>(null);
  const [unitLabel, setUnitLabel] = useState('slide');

  const handleGenerate = async () => {
    if (!file) {
      toast.error('Please choose a .pptx, .pdf, or .docx file first.');
      return;
    }
    setIsGenerating(true);
    try {
      const result = await materialQuestionService.generate({
        file,
        countPerUnit,
        mode,
        fixedCluster: mode === 'fixed_cluster' ? fixedCluster : undefined,
        topic: topic || undefined,
        courseId,
        sessionId,
      });
      if (!result.questions.length) {
        toast.error('No questions could be generated from this file.');
      } else {
        toast.success(`Generated ${result.generatedCount} question(s) from ${result.unitsProcessed} ${result.unitLabel}(s).`);
      }
      setUnitLabel(result.unitLabel);
      setPreview(result.questions);
    } catch (e: any) {
      toast.error(e?.message || 'Generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const updateQuestion = (idx: number, patch: Partial<GeneratedQuestion>) => {
    setPreview((prev) =>
      prev ? prev.map((q, i) => (i === idx ? { ...q, ...patch } : q)) : prev
    );
  };

  const updateOption = (qIdx: number, optIdx: number, value: string) => {
    setPreview((prev) =>
      prev
        ? prev.map((q, i) =>
            i === qIdx ? { ...q, options: q.options.map((o, j) => (j === optIdx ? value : o)) } : q
          )
        : prev
    );
  };

  const removeQuestion = (idx: number) => {
    setPreview((prev) => (prev ? prev.filter((_, i) => i !== idx) : prev));
  };

  const handleSaveAll = async () => {
    if (!preview || preview.length === 0) return;
    setIsSaving(true);
    try {
      const result = await materialQuestionService.bulkCreate(
        preview.map((q) => ({
          question: q.question,
          options: q.options,
          correctAnswer: q.correctAnswer,
          category: q.category,
          tags: q.tags,
          timeLimit: q.timeLimit,
          questionType: q.questionType,
          targetCluster: q.questionType === 'cluster' ? q.targetCluster ?? null : null,
          courseId,
          sessionId,
        }))
      );
      toast.success(`Saved ${result.savedCount} question(s) to the bank.`);
      onSaved();
      onClose();
    } catch (e: any) {
      toast.error(e?.message || 'Failed to save questions.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Auto-Generate Questions from Materials
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 overflow-y-auto">
          {/* ---------- STEP 1: Upload form ---------- */}
          {!preview && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Lecture file (.pptx, .pdf, .docx)
                </label>
                <input
                  type="file"
                  accept=".pptx,.pdf,.docx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-600 dark:text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-indigo-900/30 dark:file:text-indigo-300"
                />
                {file && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{file.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Topic / category label (optional)
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g., Lecture 3 - Neural Networks"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-md focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Questions per slide/page
                  </label>
                  <select
                    value={countPerUnit}
                    onChange={(e) => setCountPerUnit(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-md focus:ring-2 focus:ring-indigo-500"
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Targeting
                  </label>
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value as GenerationMode)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-md focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="difficulty">Auto by difficulty (fills all clusters)</option>
                    <option value="generic">All generic (sent to everyone)</option>
                    <option value="fixed_cluster">All for one cluster</option>
                  </select>
                </div>
              </div>

              {mode === 'fixed_cluster' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Target cluster
                  </label>
                  <select
                    value={fixedCluster}
                    onChange={(e) => setFixedCluster(e.target.value as any)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-md focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="passive">Passive (low engagement)</option>
                    <option value="moderate">Moderate</option>
                    <option value="active">Active (highly engaged)</option>
                  </select>
                </div>
              )}

              <div className="rounded-md bg-indigo-50 dark:bg-indigo-900/20 p-3 text-xs text-indigo-800 dark:text-indigo-300">
                <strong>How it works:</strong> The AI reads each {`slide/page`} and writes
                questions from that content. With "Auto by difficulty", easy questions go to
                passive, medium to moderate, hard to active students. You'll review everything
                before it's saved.
              </div>
            </div>
          )}

          {/* ---------- STEP 2: Preview ---------- */}
          {preview && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Review and edit before saving. {preview.length} question(s) ready.
              </p>
              {preview.map((q, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                        {unitLabel} {q.sourceSlide}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                        {q.difficulty}
                      </span>
                      {q.questionType === 'cluster' && q.targetCluster && (
                        <span className={`px-2 py-0.5 rounded ${clusterColors[q.targetCluster]}`}>
                          {q.targetCluster}
                        </span>
                      )}
                      {q.questionType === 'generic' && (
                        <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
                          generic
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => removeQuestion(idx)}
                      className="text-gray-400 hover:text-red-500"
                      title="Remove this question"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <textarea
                    value={q.question}
                    onChange={(e) => updateQuestion(idx, { question: e.target.value })}
                    rows={2}
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded"
                  />

                  <div className="space-y-1.5">
                    {q.options.map((opt, optIdx) => (
                      <div key={optIdx} className="flex items-center gap-2">
                        <input
                          type="radio"
                          name={`correct-${idx}`}
                          checked={q.correctAnswer === optIdx}
                          onChange={() => updateQuestion(idx, { correctAnswer: optIdx })}
                          title="Mark as correct answer"
                        />
                        <input
                          type="text"
                          value={opt}
                          onChange={(e) => updateOption(idx, optIdx, e.target.value)}
                          className={`flex-1 px-2 py-1 text-sm border rounded dark:bg-gray-700 dark:text-gray-100 ${
                            q.correctAnswer === optIdx
                              ? 'border-green-400 dark:border-green-600'
                              : 'border-gray-300 dark:border-gray-600'
                          }`}
                        />
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Type:</label>
                    <select
                      value={q.questionType}
                      onChange={(e) =>
                        updateQuestion(idx, {
                          questionType: e.target.value as 'generic' | 'cluster',
                          targetCluster:
                            e.target.value === 'cluster' ? q.targetCluster ?? 'moderate' : null,
                        })
                      }
                      className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded"
                    >
                      <option value="generic">Generic</option>
                      <option value="cluster">Cluster</option>
                    </select>
                    {q.questionType === 'cluster' && (
                      <select
                        value={q.targetCluster ?? 'moderate'}
                        onChange={(e) =>
                          updateQuestion(idx, { targetCluster: e.target.value as any })
                        }
                        className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded"
                      >
                        <option value="passive">passive</option>
                        <option value="moderate">moderate</option>
                        <option value="active">active</option>
                      </select>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 rounded-b-lg">
          {!preview ? (
            <>
              <Button variant="outline" onClick={onClose} disabled={isGenerating}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleGenerate} disabled={isGenerating || !file}>
                {isGenerating ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Generating…
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Upload className="h-4 w-4" /> Generate
                  </span>
                )}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setPreview(null)} disabled={isSaving}>
                Back
              </Button>
              <Button
                variant="primary"
                onClick={handleSaveAll}
                disabled={isSaving || preview.length === 0}
              >
                {isSaving ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Saving…
                  </span>
                ) : (
                  `Save ${preview.length} to bank`
                )}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
