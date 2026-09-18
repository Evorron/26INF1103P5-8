<h1>Hawker AI</h1>

An AI tool using consumer and seasonal trends, as well as weather forecasting to provide recommendations on the amount of food the business needs to prepare. The main scope of this project is to assist users in preventing unnecessary spending costs in resources, leading to food wastage.

<h2>1. Problem Statement and Target Users</h2>
Food wastage remains a major concern in Singapore, where limited land makes waste disposal challenging. For small food businesses such as hawkers, home-based businesses, and pop-up vendors, unpredictable customer demand can lead to over-ordering, overproduction, and unsold food. Coupled with rising food and operating costs, this creates both an environmental and financial burden, highlighting the need for a practical solution to help businesses reduce food wastage, manage costs, and improve profitability. 
Target User/Audience:
Hawkers
Pop-up Stall Vendors
Home-based food businesses

<h2>2. User Inputs</h2>
| Mandatory Inputs: | Additional Inputs: |
|----------|-------|--------|
|<b>User Profile (Business Type):</b> Are you a hawker, pop-up stall vendor, or a home-based cook?|
|</b>Operation Duration (Based on User Profile):</b> Operating Hours (Hawkers & Home-Based cook), Date of pop-up stall (How long will the event be?) 
|<b>Food Category:</b> (Savoury/Sweet; Hot/Cold Desserts; etc)|
|<b>Location:</b> (Where is the hawker store/home-based cook store/ pop-up stall located at?)|
|<b>Quantity of ingredient Ordered:</b> (Fixed Bulk Order) → Assist with food preparation|

Historical Performance (Daily/Weekly):
Crowd Density (Average Customers per day)
Sales
Any food wastage/Out of stock items
Highest & Lowest Sales Performance
Weather forecasting 
Any upcoming festive seasons? (School Holidays, Public Holidays; etc)
Event Description (Pop-up Stall Vendors)
Was Any Marketing Done to Advertise Your Store?

<h2>3. Use of AI</h2>
How will AI be utilized within the application?
Users will provide the AI with a list of considerations prior to their event.
These are considerations that can affect the business and its operational needs.
The AI will then generate insights and recommendations on how the business can manage its logistical needs.
Users will be able to enter their own collection of data to provide more context to the AI -> Providing a more granular response
What outputs, insights, or recommendations will the AI generate from the user inputs?
To provide recommendations for our hawker on the amount of ingredients to prepare in advance. 
Forecasting towards certain food/ingredients type (Eg. On a hot weather, AI would enable our hawkers to prepare more ingredients for cold desserts whereas cold weather with warm desserts)
Forecast expected crowd density for holiday seasons with historical sales
Cost effective operating methods to boost business and reduce unnecessary cost

<h2>4. Business Rules, Validations, Decision-Making logic<h2>
Business Rule (fixed rules the system follows)
AI predictions based on historical sales patterns and demand
Considerations of weekends, public holidays, other special events
AI to adhere to the conditional constraints set by the user, it's free to work with other factors that are not specified.
Compare the predicted quantity with actual sales and save it for future predictions
AI to provide disclaimers that the recommendations do not account for unpredictable circumstances (Sudden closure, Bad event planning leading to low consumer traffic, etc.)
Provides confirmation on missing or unclear data (Information missing from mandatory inputs, etc.)
Abnormal, or unusually high/low predictions must be flagged and raised an alert -> Will require hawker’s verification
Unrelated questions and topics prompted by the user will be alerted by the AI in the chat. (Will attempt to draw user back to asking relevant questions)
Decision-making logic
Users can manually override the AI recommendation. AI should adapt its output based on the overrides
Maximum and minimum preparation quantity (AI predictions must be manageable)
Closed stalls do not generate a preparation recommendation (No preparation recommendation will be generated on the day the stall is not operating)

Validations
Sales quantity must be a non-negative whole number
Date must follow a valid format (e.g. DD/MM/YYYY, Start Date-End Date, 10am-10pm→ 12hrs format)
Food ingredient must exist in the system
Weather data field must contain a valid condition (eg. rainy, stormy, sunny etc)
System must never generate negative preparation quantity
Holiday field must contain either Yes or No
