from model_utils import classifier
import pandas as pd


def train_initial_model():
    print("Preparing training data...")
    data = [
        ("Get free money now! Click here to win a prize.", 1),
        ("Urgent: Your account needs verification. Claim your gift.", 1),
        ("Congratulations! You are the winner of our lottery.", 1),
        ("Dear user, your email has been selected as a winner in the international lottery.", 1),
        ("To claim your prize, send your bank details and ID proof immediately.", 1),
        ("Lottery department notice: provide your account number to receive the reward.", 1),
        ("Claim your inheritance from the lost treasures.", 1),
        ("Verify your bank details to avoid account suspension.", 1),
        ("FINAL NOTICE: Your car insurance is about to expire.", 1),
        ("Win a $1000 Amazon gift card! Limited time offer.", 1),
        ("Work from home and earn $5000 a week! No experience needed.", 1),
        ("Click here to unlock your tax refund and confirm your bank credentials.", 1),
        ("Security alert: your mailbox will be closed unless you verify your password today.", 1),
        ("Your package is on hold. Pay a small redelivery fee immediately.", 1),
        ("Selected winner notice, submit ID proof and payment details now.", 1),
        ("Dear customer, your KYC failed. Upload PAN card and bank passbook urgently.", 1),
        ("You have won a lucky draw prize. Send your Aadhaar copy to claim it.", 1),
        ("Investment opportunity with guaranteed 300 percent return, act immediately.", 1),
        ("Your ATM card has been blocked. Share OTP to reactivate it.", 1),
        ("Crypto giveaway winner announcement, connect wallet to receive your tokens.", 1),
        ("Hi, are we still meeting for lunch today?", 0),
        ("The project report is attached for your review.", 0),
        ("Please find the invoice for last month's services.", 0),
        ("Hey, just checking in to see how you are doing.", 0),
        ("Meeting invite: Weekly sync on Monday at 10 AM.", 0),
        ("Your package is ready for pickup at the post office.", 0),
        ("Reminder: Subscription renewal for your streaming service.", 0),
        ("Can you review the PR before the release window tomorrow?", 0),
        ("Thanks for sending the updated design files.", 0),
        ("Lunch is moved to 1 PM because the client call ran long.", 0),
        ("The interview has been scheduled for Tuesday morning.", 0),
        ("Attached is the signed contract for your records.", 0),
        ("Please submit the timesheet by Friday evening.", 0),
        ("The support ticket was resolved and closed successfully.", 0),
        ("Your electricity bill has been generated and is available in the customer portal.", 0),
        ("Team outing photos are uploaded to the shared drive.", 0),
        ("Let us reschedule the doctor appointment to next week.", 0),
        ("Minutes from today's review meeting are attached below.", 0),
        ("The courier delivered the documents to reception.", 0),
        ("Please update the spreadsheet with the final budget numbers.", 0),
    ]

    df = pd.DataFrame(data, columns=["text", "label"])

    print("Training model...")
    classifier.train(df["text"], df["label"])
    print("Model trained and saved to spam_model.joblib")


if __name__ == "__main__":
    train_initial_model()
