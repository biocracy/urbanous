export interface NewsItem {
    id: string;
    title: string;
    summary: string;
    category: string;
    imageUrl?: string;
    source: string;
    date: string;
    location: string;
    coords: [number, number]; // lat, lng
    isPremium?: boolean; // For visual flair testing
}

export const MOCK_NEWS: NewsItem[] = [
    {
        id: '1',
        title: "Kyiv's Historical District Gets a Futuristic Lighting Overhaul",
        summary: "A new urban project aims to highlight the architectural heritage of Podil with adaptive smart lighting that responds to pedestrian flow and time of day.",
        category: "Urban Design",
        imageUrl: "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&q=80&w=1000",
        source: "The Kyiv Independent",
        date: "2 hours ago",
        location: "Kyiv, Ukraine",
        coords: [50.4501, 30.5234],
        isPremium: true
    },
    {
        id: '2',
        title: "Tokyo's Underground Bike Parks Reach Capacity as Cycling Surges",
        summary: "Automation and robotics are being used to stack thousands of bicycles in underground silos, but demand still outpaces supply in the world's most populous metropolis.",
        category: "Infrastructure",
        imageUrl: "https://images.unsplash.com/photo-1574906803761-ef37e54f9104?auto=format&fit=crop&q=80&w=1000",
        source: "Japan Times",
        date: "4 hours ago",
        location: "Tokyo, Japan",
        coords: [35.6762, 139.6503]
    },
    {
        id: '3',
        title: "Berlin to Ban Private Cars in Center by 2030",
        summary: "The ambitious plan would turn the entire Mitte district into a pedestrian and cyclist zone, with exceptions only for delivery and emergency vehicles.",
        category: "Policy",
        source: "Deutsche Welle",
        date: "6 hours ago",
        location: "Berlin, Germany",
        coords: [52.5200, 13.4050]
    },
    {
        id: '4',
        title: "New York's High Line Effect: How Greenways Raise Real Estate Prices",
        summary: "A new study correlates the proximity to linear parks with a 30% increase in property value, raising concerns about gentrification in the Bronx.",
        category: "Real Estate",
        imageUrl: "https://images.unsplash.com/photo-1496442226666-8d4a0e62e6e9?auto=format&fit=crop&q=80&w=1000",
        source: "NY Times",
        date: "8 hours ago",
        location: "New York, USA",
        coords: [40.7128, -74.0060],
        isPremium: true
    },
    {
        id: '5',
        title: "Solar Glass Skyscrapers: The Future of Singapore's Skyline",
        summary: "Transparent solar panels are being mandated for all new high-rises in the business district, turning windows into power plants.",
        category: "Technology",
        imageUrl: "https://images.unsplash.com/photo-1490642914619-7955a307326d?auto=format&fit=crop&q=80&w=1000",
        source: "Channel News Asia",
        date: "12 hours ago",
        location: "Singapore",
        coords: [1.3521, 103.8198]
    },
    {
        id: '6',
        title: "Paris 15-Minute City Concept Faces Backlash in Suburbs",
        summary: "While popular in the center, commuters in the banlieues argue that the decentralization plan ignores their reliance on cars for cross-town travel.",
        category: "Urbanism",
        source: "Le Monde",
        date: "1 day ago",
        location: "Paris, France",
        coords: [48.8566, 2.3522]
    }
];
