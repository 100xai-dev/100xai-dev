import Link from "next/link";

export default function BrandsPage() {
  return (
    <main>
      <header>
        <h1>Brands</h1>
        <Link href="/brands/new">Create brand</Link>
      </header>
      <p>Brand list wiring comes after API client authentication is added.</p>
    </main>
  );
}

