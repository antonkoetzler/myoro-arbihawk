import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import { stripe } from '@/lib/stripe';
import { db } from '@/db';
import { subscriptions } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { env } from '@/lib/env';

/**
 * Stripe webhook endpoint.
 *
 * Handles Stripe webhook events:
 * - checkout.session.completed: User completed payment, create subscription
 * - customer.subscription.updated: Subscription status changed
 * - customer.subscription.deleted: Subscription canceled
 */
export async function POST(req: Request) {
  if (!stripe) {
    return NextResponse.json(
      { error: 'Stripe is not configured' },
      { status: 500 }
    );
  }

  const body = await req.text();
  const signature = headers().get('stripe-signature');

  if (!signature) {
    return NextResponse.json({ error: 'No signature' }, { status: 400 });
  }

  const webhookSecret = env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return NextResponse.json(
      { error: 'Webhook secret not configured' },
      { status: 500 }
    );
  }

  let event;

  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    console.error(
      '[POST /api/webhooks/stripe]: Webhook signature verification failed:',
      error.message
    );
    return NextResponse.json({ error: error.message }, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        if (session.mode !== 'subscription' || !session.subscription) {
          break;
        }

        if (typeof session.subscription === 'string') {
          const subscription = await stripe.subscriptions.retrieve(
            session.subscription
          );

          const customerId =
            typeof subscription.customer === 'string'
              ? subscription.customer
              : subscription.customer.id;

          await db.insert(subscriptions).values({
            userId: session.metadata?.userId || '',
            leagueId: session.metadata?.leagueId || '',
            stripeSubscriptionId: subscription.id,
            stripeCustomerId: customerId,
            status: subscription.status === 'active' ? 'active' : 'incomplete',
            currentPeriodEnd: new Date(subscription.current_period_end * 1000),
          });
        }
        break;
      }

      case 'customer.subscription.updated': {
        const subscription = event.data.object;

        await db
          .update(subscriptions)
          .set({
            status:
              subscription.status === 'active'
                ? 'active'
                : subscription.status === 'canceled'
                  ? 'canceled'
                  : subscription.status === 'past_due'
                    ? 'past_due'
                    : 'incomplete',
            currentPeriodEnd: new Date(subscription.current_period_end * 1000),
            updatedAt: new Date(),
          })
          .where(eq(subscriptions.stripeSubscriptionId, subscription.id));
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = event.data.object;

        await db
          .update(subscriptions)
          .set({
            status: 'canceled',
            updatedAt: new Date(),
          })
          .where(eq(subscriptions.stripeSubscriptionId, subscription.id));
        break;
      }

      default:
        console.log(
          `[POST /api/webhooks/stripe]: Unhandled event type: ${event.type}`
        );
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('[POST /api/webhooks/stripe]: Webhook handler error:', error);
    return NextResponse.json(
      { error: 'Webhook handler failed' },
      { status: 500 }
    );
  }
}
