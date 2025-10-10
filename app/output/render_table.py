from tabulate import tabulate
def print_table(rows):
    print(tabulate(
      [(r["site"], r["title"][:60], f"Rs{r['price_inr']:,}", r.get("rating",0.0), r["url"][:80] + "..." if len(r["url"]) > 80 else r["url"]) for r in rows],
      headers=["Site","Title","Price","Rating","Link"], tablefmt="grid"))
