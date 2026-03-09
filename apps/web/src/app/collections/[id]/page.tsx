'use client';

import { use } from 'react';
import Link from 'next/link';
import { ArrowLeft, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  useCollection,
  useCollectionItems,
  useRemoveFromCollection,
} from '@/hooks/use-collections';
import { formatDistanceToNow } from 'date-fns';

export default function CollectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: collection, isLoading } = useCollection(id);
  const { data: items, isLoading: itemsLoading } = useCollectionItems(id);
  const removeItem = useRemoveFromCollection();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!collection) {
    return (
      <div className="text-center py-16">
        <p className="text-destructive">Collection not found.</p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/collections">Back to Collections</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/collections">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {collection.name}
          </h1>
          {collection.description && (
            <p className="text-muted-foreground mt-1">
              {collection.description}
            </p>
          )}
          <p className="text-sm text-muted-foreground mt-1">
            {collection.item_count} items / Created{' '}
            {formatDistanceToNow(new Date(collection.created_at), {
              addSuffix: true,
            })}
          </p>
        </div>
      </div>

      {itemsLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : !items || items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No items in this collection yet.</p>
          <p className="text-sm mt-1">
            Add items from search results to build your collection.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {item.result ? (
                      <>
                        <p className="text-sm font-medium truncate">
                          {item.result.caption || 'No caption'}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {item.result.platform}
                          </Badge>
                          {item.result.creator_handle && (
                            <span className="text-xs text-muted-foreground">
                              @{item.result.creator_handle}
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground">
                            Score: {Math.round(item.result.score * 100)}%
                          </span>
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Result ID: {item.result_id}
                      </p>
                    )}
                    {item.notes && (
                      <p className="text-sm text-muted-foreground mt-2 bg-muted p-2 rounded">
                        {item.notes}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      Added{' '}
                      {formatDistanceToNow(new Date(item.added_at), {
                        addSuffix: true,
                      })}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() =>
                      removeItem.mutate({
                        collectionId: id,
                        itemId: item.id,
                      })
                    }
                    disabled={removeItem.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
