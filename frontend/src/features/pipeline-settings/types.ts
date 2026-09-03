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
  type: "number" | "boolean" | "readonly" | "membership";
  min?: number;
  max?: number;
  step?: number;
  defaultValue: any;
  member?: string;
  readonlyValue?: string;
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
