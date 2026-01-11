export interface ArticleScores {
    topic: number;
    date: number;
    geo?: number;
    is_fresh?: boolean;
}

export interface Article {
    title: string;
    url: string;
    source: string;
    date_str?: string;
    relevance_score: number;
    scores?: ArticleScores;
    ai_verdict?: string; // "VERIFIED" or other
    translated_title?: string;
}

export interface DigestReportRendererProps {
    articles: Article[];
    category: string;
    isTranslated?: boolean;
    selectedUrls: Set<string>;
    onToggle: (url: string) => void;
    onAssess?: (article: Article) => void;
    onDebug?: (article: Article) => void;
}
