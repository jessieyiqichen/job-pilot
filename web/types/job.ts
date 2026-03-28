export interface JobWithScore {
  id: number;
  job_id: string;
  platform: string;
  title: string;
  company: string;
  salary_min: number | null;
  salary_max: number | null;
  city: string | null;
  experience: string | null;
  education: string | null;
  jd_text: string | null;
  discovered_at: string | null;
  status: string;
  // Score fields (null if not scored)
  overall_score: number | null;
  skill_match: number | null;
  experience_match: number | null;
  salary_match: number | null;
  highlights: string[];
  concerns: string[];
  suggestion: string | null;
  scored_at: string | null;
  source_url: string | null;
}

export interface PipelineStats {
  funnel: { stage: string; count: number }[];
  scoreDistribution: { bucket: number; count: number }[];
  sourceBreakdown: { platform: string; count: number }[];
}
