export type PipelineSectionId =
  | "overview"
  | "enrichment"
  | "screening"
  | "shortlisting"
  | "ranking"
  | "cv-analysis"
  | "cv-generation"
  | "runtime-limits"
  | "automation-reuse";

export interface PipelineFieldDef {
  key: string;
  label: string;
  description: string;
  type: "number" | "boolean" | "readonly" | "membership" | "select";
  min?: number;
  max?: number;
  step?: number;
  defaultValue: any;
  member?: string;
  readonlyValue?: string;
  options?: Array<{ value: string; label: string }>;
}

export interface PipelineGroupDef {
  title: string;
  description?: string;
  fields: PipelineFieldDef[];
}

export interface PipelineSectionDef {
  id: PipelineSectionId;
  title: string;
  description: string;
  groups: PipelineGroupDef[];
  ownedKeys: string[];
}
