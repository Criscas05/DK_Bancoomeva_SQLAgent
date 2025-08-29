export interface message{
    content:string;
    role:string;
    id:string;
}

export interface AssistantMessage {
  id: string;
  answer: string;
  table: { [key: string]: string }[];
  columns: string[];
  sql: string;
}
