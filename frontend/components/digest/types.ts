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
    is_spam?: boolean;
}

export interface DigestReportRendererProps {
    articles: Article[];
    category: string;
    isTranslated?: boolean;
    selectedUrls: Set<string>;
    onToggle: (url: string) => void;
    onAssess?: (article: Article) => void;
    onDebug?: (article: Article) => void;
    onReportSpam?: (article: Article) => void;
    spamUrls?: Set<string>;
    excludedArticles?: Article[];
}

export interface Digest {
    id: number;
    title: string;
    category: string;
    city?: string;
    timeframe?: string;
    created_at: string;
    is_public?: boolean;
    public_slug?: string;

    // Ownership
    owner_id: number;
    owner_username?: string;
    owner_is_visible: boolean;
}
