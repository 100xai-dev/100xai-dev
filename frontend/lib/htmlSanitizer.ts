/**
 * HTML Sanitization utilities to prevent XSS attacks
 * Uses DOMPurify to safely render user/LLM-generated HTML content
 */

import DOMPurify from 'dompurify';

/**
 * Configuration for blog content sanitization
 * Allows safe HTML tags typically found in blog articles while removing dangerous elements
 */
const BLOG_CONTENT_CONFIG = {
  // Allow only safe HTML tags for blog content
  ALLOWED_TAGS: [
    'p', 'br', 'strong', 'em', 'b', 'i', 'u', 'a', 
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
    'div', 'span', 'img'
  ],
  // Allow only safe attributes
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'title', 'class', 'id', 'target', 'rel'
  ],
  // Remove dangerous protocols
  ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  // Additional security measures
  ALLOW_DATA_ATTR: false,
  ALLOW_UNKNOWN_PROTOCOLS: false,
  KEEP_CONTENT: true
};

/**
 * Sanitizes HTML content for safe rendering in blog articles
 * Removes XSS vectors while preserving safe formatting
 */
export function sanitizeBlogContent(htmlContent: string): string {
  if (!htmlContent || typeof htmlContent !== 'string') {
    return '';
  }

  try {
    return DOMPurify.sanitize(htmlContent, BLOG_CONTENT_CONFIG);
  } catch (error) {
    console.error('HTML sanitization failed:', error);
    // Fallback: strip all HTML tags if sanitization fails
    return htmlContent.replace(/<[^>]*>/g, '');
  }
}

/**
 * Cleans generator artifacts out of a blog draft before it is rendered as a
 * finished post: stray markdown code fences (```html / ```) that the section
 * LLM sometimes emits, and a leading <h1> — the preview shows the title in its
 * own header, so an embedded one would render as a duplicate.
 */
export function cleanBlogDraftHtml(htmlContent: string): string {
  if (!htmlContent || typeof htmlContent !== 'string') return '';
  return htmlContent
    .replace(/```[a-zA-Z]*/g, '')
    .replace(/<h1[^>]*>[\s\S]*?<\/h1>/i, '')
    .trim();
}

/**
 * React hook for safely rendering HTML content
 * Returns sanitized HTML that can be safely used with dangerouslySetInnerHTML
 */
export function useSafeHTML(htmlContent: string): { __html: string } {
  const sanitizedHTML = sanitizeBlogContent(htmlContent);
  return { __html: sanitizedHTML };
}

/**
 * Strict sanitization for user input (more restrictive)
 * Only allows basic formatting, no links or images
 */
export function sanitizeUserInput(htmlContent: string): string {
  const strictConfig = {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'b', 'i'],
    ALLOWED_ATTR: [],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    KEEP_CONTENT: true
  };

  try {
    return DOMPurify.sanitize(htmlContent, strictConfig);
  } catch (error) {
    console.error('Strict HTML sanitization failed:', error);
    return htmlContent.replace(/<[^>]*>/g, '');
  }
}