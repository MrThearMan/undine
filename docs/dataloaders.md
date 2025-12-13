description: DataLoader support in Undine

# DataLoaders

In this section, we'll cover Undine's `DataLoader` class, which is a utility
class for loading data in batches. `DataLoaders` can be used to optimize the performance
of queries that require I/O operations, like fetching data from an external API.

> Note: In most cases, using `DataLoaders` to optimize database queries is not necessary,
> as Undine's [Optimizer](optimizer.md) already handles this for you.

## DataLoader

```python
-8<- "dataloaders/dataloader.py"
```
