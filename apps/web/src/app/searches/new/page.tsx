'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useCreateSearch } from '@/hooks/use-searches';
import type { Platform } from '@/lib/types';
import Link from 'next/link';

const platforms: Platform[] = ['tiktok', 'instagram', 'youtube', 'twitter', 'other'];

export default function NewSearchPage() {
  const router = useRouter();
  const createSearch = useCreateSearch();

  const [query, setQuery] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([]);
  const [region, setRegion] = useState('');
  const [language, setLanguage] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [maxResults, setMaxResults] = useState(100);
  const [includeFilters, setIncludeFilters] = useState('');
  const [excludeFilters, setExcludeFilters] = useState('');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [error, setError] = useState('');

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!query.trim()) {
      setError('Query is required');
      return;
    }

    try {
      const search = await createSearch.mutateAsync({
        raw_query: query.trim(),
        platforms: selectedPlatforms.length > 0 ? selectedPlatforms : undefined,
        region: region || undefined,
        language: language || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        max_results: maxResults,
        include_filters: includeFilters
          ? { terms: includeFilters.split('\n').filter(Boolean) }
          : undefined,
        exclude_filters: excludeFilters
          ? { terms: excludeFilters.split('\n').filter(Boolean) }
          : undefined,
        confidence_threshold: confidenceThreshold,
      });
      router.push(`/searches/${search.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create search');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/searches">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Search</h1>
          <p className="text-muted-foreground mt-1">
            Configure and launch a new content search
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
            {error}
          </div>
        )}

        {/* Query */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Search Query</CardTitle>
            <CardDescription>
              Describe the video content you are looking for
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              placeholder="e.g. cooking tutorials featuring pasta dishes with professional lighting"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              required
            />
          </CardContent>
        </Card>

        {/* Platforms */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Platforms</CardTitle>
            <CardDescription>
              Select platforms to search (leave empty for all)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {platforms.map((platform) => (
                <button
                  key={platform}
                  type="button"
                  onClick={() => togglePlatform(platform)}
                  className={`px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
                    selectedPlatforms.includes(platform)
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-accent border-input'
                  }`}
                >
                  {platform.charAt(0).toUpperCase() + platform.slice(1)}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="region">Region</Label>
                <Select
                  id="region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                >
                  <option value="">Any region</option>
                  <option value="us">United States</option>
                  <option value="gb">United Kingdom</option>
                  <option value="eu">Europe</option>
                  <option value="asia">Asia</option>
                  <option value="latam">Latin America</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="language">Language</Label>
                <Select
                  id="language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="">Any language</option>
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="pt">Portuguese</option>
                  <option value="zh">Chinese</option>
                  <option value="ja">Japanese</option>
                  <option value="ko">Korean</option>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dateFrom">Date From</Label>
                <Input
                  id="dateFrom"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dateTo">Date To</Label>
                <Input
                  id="dateTo"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Max Results: {maxResults}</Label>
              <Slider
                min={10}
                max={500}
                step={10}
                value={[maxResults]}
                onValueChange={([v]) => setMaxResults(v)}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>10</span>
                <span>500</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Confidence Threshold: {confidenceThreshold.toFixed(2)}</Label>
              <Slider
                min={0}
                max={1}
                step={0.05}
                value={[confidenceThreshold]}
                onValueChange={([v]) => setConfidenceThreshold(v)}
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0 (Include all)</span>
                <span>1 (Very strict)</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="includeFilters">Include Filters (one per line)</Label>
              <Textarea
                id="includeFilters"
                placeholder="e.g. has_speech&#10;high_quality"
                value={includeFilters}
                onChange={(e) => setIncludeFilters(e.target.value)}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="excludeFilters">Exclude Filters (one per line)</Label>
              <Textarea
                id="excludeFilters"
                placeholder="e.g. nsfw&#10;low_resolution"
                value={excludeFilters}
                onChange={(e) => setExcludeFilters(e.target.value)}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" disabled={createSearch.isPending} className="flex-1">
            {createSearch.isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            Launch Search
          </Button>
          <Button type="button" variant="outline" asChild>
            <Link href="/searches">Cancel</Link>
          </Button>
        </div>
      </form>
    </div>
  );
}
