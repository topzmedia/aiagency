'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Plus, FolderOpen, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useCollections, useCreateCollection } from '@/hooks/use-collections';
import { formatDistanceToNow } from 'date-fns';

export default function CollectionsPage() {
  const { data: collections, isLoading, error } = useCollections();
  const createCollection = useCreateCollection();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      await createCollection.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName('');
      setDescription('');
      setDialogOpen(false);
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Collections</h1>
          <p className="text-muted-foreground mt-1">
            Organize and save your favorite results
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Collection
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleCreate}>
              <DialogHeader>
                <DialogTitle>Create Collection</DialogTitle>
                <DialogDescription>
                  Create a new collection to organize your results.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="e.g. Best Cooking Videos"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="What is this collection for?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createCollection.isPending}>
                  {createCollection.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  )}
                  Create
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="text-center py-16 text-destructive">
          <p>Failed to load collections.</p>
        </div>
      ) : !collections || collections.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No collections yet</p>
          <p className="text-sm">Create your first collection to organize results</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {collections.map((collection) => (
            <Link key={collection.id} href={`/collections/${collection.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <CardTitle className="text-lg">{collection.name}</CardTitle>
                  {collection.description && (
                    <CardDescription>{collection.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{collection.item_count} items</span>
                    <span>
                      {formatDistanceToNow(new Date(collection.created_at), {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
