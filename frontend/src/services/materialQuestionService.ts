// Service for AI question generation from uploaded lecture materials.

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getAuthToken = (): string => {
  const token = sessionStorage.getItem('access_token');
  if (!token) throw new Error('Not authenticated. Please log in again.');
  return token;
};

const getUserRole = (): string => {
  try {
    const user = sessionStorage.getItem('user');
    if (user) return JSON.parse(user).role || 'student';
  } catch {
    /* ignore */
  }
  return 'student';
};

export interface GeneratedQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard';
  explanation?: string;
  sourceSlide: number;
  unitLabel: string;
  questionType: 'generic' | 'cluster';
  targetCluster?: 'passive' | 'moderate' | 'active' | null;
  timeLimit: number;
  tags: string[];
}

export interface GenerateResult {
  success: boolean;
  unitLabel: string;
  unitsProcessed: number;
  generatedCount: number;
  topic: string;
  courseId?: string;
  sessionId?: string;
  questions: GeneratedQuestion[];
}

export type GenerationMode = 'difficulty' | 'generic' | 'fixed_cluster';

export const materialQuestionService = {
  async generate(params: {
    file: File;
    countPerUnit: number;
    mode: GenerationMode;
    fixedCluster?: 'passive' | 'moderate' | 'active';
    topic?: string;
    courseId?: string;
    sessionId?: string;
  }): Promise<GenerateResult> {
    const form = new FormData();
    form.append('file', params.file);
    form.append('count_per_unit', String(params.countPerUnit));
    form.append('mode', params.mode);
    if (params.fixedCluster) form.append('fixed_cluster', params.fixedCluster);
    if (params.topic) form.append('topic', params.topic);
    if (params.courseId) form.append('course_id', params.courseId);
    if (params.sessionId) form.append('session_id', params.sessionId);

    const response = await fetch(`${API_BASE_URL}/api/questions/generate-from-material`, {
      method: 'POST',
      headers: {
        // NOTE: do NOT set Content-Type — the browser sets the multipart boundary.
        Authorization: `Bearer ${getAuthToken()}`,
        'x-user-role': getUserRole(),
      },
      body: form,
    });

    if (!response.ok) {
      const text = await response.text();
      let message = `Generation failed: ${response.status}`;
      try {
        message = JSON.parse(text).detail || message;
      } catch {
        if (text) message = text;
      }
      throw new Error(message);
    }
    return await response.json();
  },

  async bulkCreate(questions: Array<{
    question: string;
    options: string[];
    correctAnswer: number;
    category: string;
    tags?: string[];
    timeLimit?: number;
    questionType?: 'generic' | 'cluster';
    targetCluster?: 'passive' | 'moderate' | 'active' | null;
    courseId?: string;
    sessionId?: string;
  }>): Promise<{ success: boolean; savedCount: number; failedCount: number; ids: string[] }> {
    const response = await fetch(`${API_BASE_URL}/api/questions/bulk-create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getAuthToken()}`,
        'x-user-role': getUserRole(),
      },
      body: JSON.stringify({ questions }),
    });

    if (!response.ok) {
      const text = await response.text();
      let message = `Save failed: ${response.status}`;
      try {
        message = JSON.parse(text).detail || message;
      } catch {
        if (text) message = text;
      }
      throw new Error(message);
    }
    return await response.json();
  },
};
