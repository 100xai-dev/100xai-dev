"use client";

export function CreateBrandForm() {
  return (
    <form>
      <label>
        Brand name
        <input name="name" required />
      </label>
      <label>
        Website URL
        <input name="website_url" type="url" />
      </label>
      <fieldset>
        <legend>DNA source</legend>
        <label>
          <input defaultChecked name="dna_source" type="radio" value="crawl" />
          Crawl website
        </label>
        <label>
          <input name="dna_source" type="radio" value="manual" />
          Manual profile
        </label>
      </fieldset>
      <button type="submit">Create</button>
    </form>
  );
}

