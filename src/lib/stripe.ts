import Stripe from 'stripe';

/**
 * Stripe client instance.
 *
 * Initialized with secret key from environment variables.
 * Used for creating checkout sessions, managing subscriptions, and handling webhooks.
 *
 * Returns null if STRIPE_SECRET_KEY is not configured (for development).
 */
export const stripe = process.env.STRIPE_SECRET_KEY
  ? new Stripe(process.env.STRIPE_SECRET_KEY, {
      apiVersion: '2025-12-15.clover',
      typescript: true,
    })
  : null;

/**
 * Creates a Stripe checkout session for league subscription.
 *
 * @param userId - User ID from database
 * @param userEmail - User email address
 * @param leagueId - League ID from database
 * @param leagueName - League name for display
 * @param priceId - Stripe price ID for the league subscription
 * @returns Stripe checkout session
 */
export async function createCheckoutSession(
  userId: string,
  userEmail: string,
  leagueId: string,
  leagueName: string,
  priceId: string
): Promise<Stripe.Checkout.Session> {
  if (!stripe) {
    throw new Error('Stripe is not configured. Please set STRIPE_SECRET_KEY.');
  }

  const session = await stripe.checkout.sessions.create({
    customer_email: userEmail,
    payment_method_types: ['card'],
    mode: 'subscription',
    line_items: [
      {
        price: priceId,
        quantity: 1,
      },
    ],
    success_url: `${
      process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
    }/subscriptions?success=true`,
    cancel_url: `${
      process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
    }/leagues?canceled=true`,
    metadata: {
      userId,
      leagueId,
    },
  });

  return session;
}

/**
 * Retrieves a Stripe subscription by ID.
 *
 * @param subscriptionId - Stripe subscription ID
 * @returns Stripe subscription object
 */
export async function getSubscription(
  subscriptionId: string
): Promise<Stripe.Subscription> {
  if (!stripe) {
    throw new Error('Stripe is not configured. Please set STRIPE_SECRET_KEY.');
  }

  return stripe.subscriptions.retrieve(subscriptionId);
}

/**
 * Cancels a Stripe subscription.
 *
 * @param subscriptionId - Stripe subscription ID
 * @returns Canceled Stripe subscription object
 */
export async function cancelSubscription(
  subscriptionId: string
): Promise<Stripe.Subscription> {
  if (!stripe) {
    throw new Error('Stripe is not configured. Please set STRIPE_SECRET_KEY.');
  }

  return stripe.subscriptions.cancel(subscriptionId);
}
