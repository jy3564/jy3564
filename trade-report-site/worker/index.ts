import { Hono } from 'hono';
import { SignJWT, jwtVerify } from 'jose';
import { MiddlewareHandler } from 'hono/types';

// Define the environment bindings.
// These must match the bindings in wrangler.toml
export interface Env {
	DB: D1Database;
	MEDIA_BUCKET: R2Bucket;
}

// Initialize Hono with the environment bindings
const app = new Hono<{ Bindings: Env }>();

// Simple welcome route
app.get('/', (c) => {
	return c.text('Hello from Hono!');
});

// We will add more routes here, like /api/register and /api/login
app.post('/api/register', async (c) => {
	try {
		const { email, password } = await c.req.json();

		// Basic validation
		if (!email || !password || password.length < 8) {
			return c.json({ error: 'Email and a password of at least 8 characters are required' }, 400);
		}

		// Hash the password using the Web Crypto API
		const passwordBuffer = new TextEncoder().encode(password);
		const hashBuffer = await crypto.subtle.digest('SHA-256', passwordBuffer);
		const passwordHash = Array.from(new Uint8Array(hashBuffer))
			.map((b) => b.toString(16).padStart(2, '0'))
			.join('');

		// Insert user into the database
		const statement = c.env.DB.prepare('INSERT INTO users (email, password_hash) VALUES (?, ?)');
		await statement.bind(email, passwordHash).run();

		return c.json({ success: true, message: 'User registered successfully' }, 201);
	} catch (e: any) {
		// Check for unique constraint violation
		if (e.message?.includes('UNIQUE constraint failed')) {
			return c.json({ error: 'Email already in use' }, 409);
		}
		console.error('Registration error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});

// In a real application, this should be a strong, random secret
// stored securely in Cloudflare's environment variables (Secrets)
const JWT_SECRET = new TextEncoder().encode('a-very-secret-and-strong-key-that-should-be-changed');

app.post('/api/login', async (c) => {
	try {
		const { email, password } = await c.req.json();

		if (!email || !password) {
			return c.json({ error: 'Email and password are required' }, 400);
		}

		// Find the user by email
		const statement = c.env.DB.prepare('SELECT id, email, password_hash, role FROM users WHERE email = ?');
		const user = await statement.bind(email).first<{ id: number; password_hash: string; role: string }>();

		if (!user) {
			return c.json({ error: 'Invalid credentials' }, 401); // User not found
		}

		// Hash the provided password to compare with the stored hash
		const passwordBuffer = new TextEncoder().encode(password);
		const hashBuffer = await crypto.subtle.digest('SHA-256', passwordBuffer);
		const providedPasswordHash = Array.from(new Uint8Array(hashBuffer))
			.map((b) => b.toString(16).padStart(2, '0'))
			.join('');

		// Compare hashes
		if (providedPasswordHash !== user.password_hash) {
			return c.json({ error: 'Invalid credentials' }, 401); // Password incorrect
		}

		// Create JWT
		const token = await new SignJWT({ userId: user.id, role: user.role })
			.setProtectedHeader({ alg: 'HS256' })
			.setIssuedAt()
			.setExpirationTime('24h') // Token expires in 24 hours
			.sign(JWT_SECRET);

		return c.json({ success: true, token });
	} catch (e: any) {
		console.error('Login error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});

const authMiddleware: MiddlewareHandler = async (c, next) => {
	const authHeader = c.req.header('Authorization');
	if (!authHeader || !authHeader.startsWith('Bearer ')) {
		return c.json({ error: 'Unauthorized' }, 401);
	}

	const token = authHeader.substring(7);
	try {
		const { payload } = await jwtVerify(token, JWT_SECRET);
		c.set('user', payload);
		await next();
	} catch (err) {
		return c.json({ error: 'Invalid token' }, 401);
	}
};

const adminOnly: MiddlewareHandler = async (c, next) => {
	const user = c.get('user');
	if (!user || user.role !== 'admin') {
		return c.json({ error: 'Forbidden' }, 403);
	}
	await next();
};


// Protected route for creating a report
app.post('/api/reports', authMiddleware, adminOnly, async (c) => {
	try {
		const { title, content } = await c.req.json();
		const user = c.get('user');

		if (!title || !content) {
			return c.json({ error: 'Title and content are required' }, 400);
		}

		const statement = c.env.DB.prepare(
			'INSERT INTO reports (title, content, author_id) VALUES (?, ?, ?)'
		);
		const { success } = await statement.bind(title, content, user.userId).run();

		if (success) {
			return c.json({ message: 'Report created successfully' }, 201);
		} else {
			return c.json({ error: 'Failed to create report' }, 500);
		}
	} catch (e: any) {
		console.error('Report creation error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});


// Get all reports (for logged-in users)
app.get('/api/reports', authMiddleware, async (c) => {
	try {
		const statement = c.env.DB.prepare(`
      SELECT r.id, r.title, r.created_at, u.email as authorEmail
      FROM reports r
      JOIN users u ON r.author_id = u.id
      ORDER BY r.created_at DESC
    `);
		const { results } = await statement.all();
		return c.json(results);
	} catch (e: any) {
		console.error('Get reports error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});

// Get a single report by ID (for logged-in users)
app.get('/api/reports/:id', authMiddleware, async (c) => {
	try {
		const { id } = c.req.param();
		const statement = c.env.DB.prepare(`
      SELECT r.id, r.title, r.content, r.created_at, u.email as authorEmail
      FROM reports r
      JOIN users u ON r.author_id = u.id
      WHERE r.id = ?
    `);
		const report = await statement.bind(id).first();

		if (report) {
			return c.json(report);
		} else {
			return c.json({ error: 'Report not found' }, 404);
		}
	} catch (e: any) {
		console.error('Get single report error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});


// This should also be a securely stored secret for the webhook
const WEBHOOK_SECRET = 'a-very-secret-webhook-key';

app.post('/api/webhook/tradingview', async (c) => {
	// 1. Authenticate the webhook
	const incomingSecret = c.req.header('X-Webhook-Secret');
	if (incomingSecret !== WEBHOOK_SECRET) {
		return c.json({ error: 'Invalid webhook secret' }, 401);
	}

	try {
		// 2. Get the raw text body
		const rawContent = await c.req.text();

		// 3. (Optional but good practice) Parse the content.
		// For now, we will store the raw content as requested.
		// A future improvement would be to parse this into a JSON object.
		const parsedContent = {}; // Placeholder for future parsing logic

		// 4. Insert the new signal
		const insertStmt = c.env.DB.prepare('INSERT INTO signals (raw_content, parsed_content) VALUES (?, ?)');
		await insertStmt.bind(rawContent, JSON.stringify(parsedContent)).run();

		// 5. Keep only the last 5 signals
		// This query finds the ID of the 5th most recent signal, then deletes all signals older than that one.
		const deleteStmt = c.env.DB.prepare(`
      DELETE FROM signals
      WHERE id NOT IN (
        SELECT id FROM signals ORDER BY received_at DESC LIMIT 5
      )
    `);
		await deleteStmt.run();

		return c.json({ success: true, message: 'Signal received' });
	} catch (e: any) {
		console.error('Webhook error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});


// Get the latest 5 signals (for logged-in users)
app.get('/api/signals', authMiddleware, async (c) => {
	try {
		const statement = c.env.DB.prepare(
			'SELECT id, raw_content, received_at FROM signals ORDER BY received_at DESC LIMIT 5'
		);
		const { results } = await statement.all();
		return c.json(results);
	} catch (e: any) {
		console.error('Get signals error:', e);
		return c.json({ error: 'An internal error occurred' }, 500);
	}
});


// Export the app
export default app;
