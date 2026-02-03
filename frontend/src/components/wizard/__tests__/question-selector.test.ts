import { describe, it, expect } from 'vitest';
import { QuestionSelectorImpl, createQuestionSelector } from '../question-selector';

function runGamifiedPath(selector: QuestionSelectorImpl): void {
  selector.initialize({ ageGroup: 'under-19', experiencePoints: 0 });
  let q = selector.getNextQuestion();
  while (q) {
    selector.submitAnswer(q.id, 2, 15);
    q = selector.getNextQuestion();
  }
}

function runAdaptivePath(
  selector: QuestionSelectorImpl,
  anchorAnswers: [number, number, number, number]
): void {
  selector.initialize({ ageGroup: 'above-19', experiencePoints: 2 });
  const anchorIds = ['M2', 'M3', 'PT-2', 'PT-6'];
  for (let i = 0; i < 4; i++) {
    const q = selector.getNextQuestion();
    expect(q).toBeTruthy();
    expect(q!.id).toBe(anchorIds[i]);
    selector.submitAnswer(q!.id, anchorAnswers[i], 12);
  }
  // Phase 2: 4 questions
  for (let i = 0; i < 4; i++) {
    const q = selector.getNextQuestion();
    expect(q).toBeTruthy();
    selector.submitAnswer(q!.id, 3, 10);
  }
  // Phase 3: up to 4 more (gaps + PT-13 + consistency)
  let phase3Count = 0;
  let q = selector.getNextQuestion();
  while (q && phase3Count < 4) {
    selector.submitAnswer(q.id, 2, 10);
    phase3Count++;
    q = selector.getNextQuestion();
  }
  // May need one more if we didn't hit 12
  while (!selector.isComplete() && (q = selector.getNextQuestion())) {
    selector.submitAnswer(q.id, 2, 10);
  }
}

describe('question-selector', () => {
  describe('gamified path (under-19)', () => {
    it('initialize sets gamified mode and first question is story-1', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'under-19', experiencePoints: 0 });
      const q = selector.getNextQuestion();
      expect(q).toBeTruthy();
      expect(q!.id).toBe('story-1');
      expect(q!.group).toBe('PROSPECT');
      expect(q!.maxScore).toBe(4);
      expect(selector.getBranchingPath()).toBe('gamified');
      expect(selector.getState()).toBeNull();
    });

    it('returns 5 questions in order story-1 through story-5', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'under-19', experiencePoints: 0 });
      const ids: string[] = [];
      let q = selector.getNextQuestion();
      while (q) {
        ids.push(q.id);
        selector.submitAnswer(q.id, 2, 10);
        q = selector.getNextQuestion();
      }
      expect(ids).toEqual(['story-1', 'story-2', 'story-3', 'story-4', 'story-5']);
    });

    it('isComplete after 5 answers', () => {
      const selector = new QuestionSelectorImpl();
      runGamifiedPath(selector);
      expect(selector.isComplete()).toBe(true);
      expect(selector.getNextQuestion()).toBeNull();
      expect(selector.getSelectedQuestions().length).toBe(5);
    });
  });

  describe('conservative path (low Phase 1 score)', () => {
    it('phase1 score < 30 selects conservative path and Phase 2 pool is M5, M8, PT-1, PT-4', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'above-19', experiencePoints: 1 });
      const anchorIds = ['M2', 'M3', 'PT-2', 'PT-6'];
      for (let i = 0; i < 4; i++) {
        const q = selector.getNextQuestion();
        expect(q!.id).toBe(anchorIds[i]);
        selector.submitAnswer(q!.id, 1, 10);
      }
      expect(selector.getState()!.selected_path).toBe('conservative');
      expect(selector.getBranchingPath()).toBe('conservative');
      const next = selector.getNextQuestion();
      expect(next).toBeTruthy();
      expect(['M5', 'M8', 'PT-1', 'PT-4']).toContain(next!.id);
    });
  });

  describe('aggressive path (high Phase 1 score)', () => {
    it('phase1 score > 70 selects aggressive path and Phase 2 pool is M4, M11, PT-8, PT-10', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'above-19', experiencePoints: 2 });
      selector.submitAnswer('M2', 5, 10);
      selector.submitAnswer('M3', 5, 10);
      selector.submitAnswer('PT-2', 4, 10);
      selector.submitAnswer('PT-6', 4, 10);
      expect(selector.getState()!.selected_path).toBe('aggressive');
      expect(selector.getBranchingPath()).toBe('aggressive');
      const next = selector.getNextQuestion();
      expect(next).toBeTruthy();
      expect(['M4', 'M11', 'PT-8', 'PT-10']).toContain(next!.id);
    });
  });

  describe('moderate path (middle Phase 1 score)', () => {
    it('phase1 score 30–70 selects moderate path and Phase 2 pool is M6, M10, PT-3, PT-7', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'above-19', experiencePoints: 1 });
      selector.submitAnswer('M2', 3, 10);
      selector.submitAnswer('M3', 3, 10);
      selector.submitAnswer('PT-2', 2, 10);
      selector.submitAnswer('PT-6', 2, 10);
      expect(selector.getState()!.selected_path).toBe('moderate');
      const next = selector.getNextQuestion();
      expect(next).toBeTruthy();
      expect(['M6', 'M10', 'PT-3', 'PT-7']).toContain(next!.id);
    });
  });

  describe('construct coverage and Phase 3', () => {
    it('Phase 3 includes PT-13 when run to completion and completes with 12 questions', () => {
      const selector = new QuestionSelectorImpl();
      runAdaptivePath(selector, [2, 2, 2, 2]);
      expect(selector.isComplete()).toBe(true);
      const selected = selector.getSelectedQuestions().map((q) => q.id);
      expect(selected).toContain('PT-13');
      expect(selected.length).toBe(12);
    });

    it('getSelectedQuestions returns ordered list of questions asked', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'above-19', experiencePoints: 0 });
      selector.submitAnswer('M2', 3, 10);
      selector.submitAnswer('M3', 3, 10);
      const list = selector.getSelectedQuestions();
      expect(list.length).toBe(2);
      expect(list[0].id).toBe('M2');
      expect(list[1].id).toBe('M3');
    });
  });

  describe('construct coverage verification', () => {
    it('getSelectedQuestions returns questions with id, group, maxScore, construct', () => {
      const selector = new QuestionSelectorImpl();
      selector.initialize({ ageGroup: 'above-19', experiencePoints: 0 });
      const q = selector.getNextQuestion();
      expect(q).toBeTruthy();
      expect(q!.id).toBe('M2');
      expect(q!.group).toBe('MPT');
      expect(q!.maxScore).toBe(5);
      expect(q!.construct).toBe('time_horizon');
      selector.submitAnswer('M2', 3, 10);
      const list = selector.getSelectedQuestions();
      expect(list[0].id).toBe('M2');
      expect(list[0].construct).toBe('time_horizon');
    });
  });

  describe('createQuestionSelector', () => {
    it('returns instance with same interface', () => {
      const selector = createQuestionSelector();
      selector.initialize({ ageGroup: 'under-19', experiencePoints: 0 });
      expect(selector.getNextQuestion()).toBeTruthy();
      expect(selector.getBranchingPath()).toBe('gamified');
    });
  });
});
