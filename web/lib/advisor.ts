// Advisor snapshot baked into the static build by
// scripts/export_advisor_snapshot.py. The deterministic diagnosis + weekly plan
// always present; `advice` (the Claude narrative) present when generated with a
// key. Source of truth lives in Python (advisor.py / planner.py).

import snapshot from '../demo-data/advisor.json';

export interface FunnelStage {
  label: string;
  count: number;
}

export interface PlanItem {
  title: string;
  company: string;
  score: number;
  ready: boolean;
  reason: string;
}

export interface FollowUp {
  title: string;
  days_since: number;
}

export interface AdvisorSnapshot {
  headline: string;
  funnel: FunnelStage[];
  signals: {
    high_score_total: number;
    high_score_applied: number;
    high_score_tailored: number;
    total_applications: number;
    replied: number;
    interview: number;
    offer: number;
    rejected: number;
    recent_applied: number;
    stale: number;
  };
  plan: {
    weekly_target: number;
    recent_applied: number;
    note: string;
    to_apply: PlanItem[];
    follow_ups: FollowUp[];
  };
  advice: string;
  generated_at: string;
}

export const ADVISOR: AdvisorSnapshot = snapshot as AdvisorSnapshot;
