
import sqlite3 
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse


def get_polling_unit_results(polling_unit_id):
    try:
        conn = sqlite3.connect("data.sqlite")
        cursor = conn.cursor()
        
        query = """
        SELECT pu.polling_unit_id, pu.polling_unit_name, apr.party_abbreviation, apr.party_score
        FROM polling_unit pu
        JOIN announced_pu_results apr ON pu.uniqueid = apr.polling_unit_uniqueid
        WHERE polling_unit_id = ?;
        """
        
        cursor.execute(query, (polling_unit_id,))
        results = cursor.fetchall()
        
        conn.close()
        return results
    except Exception as e:
        print(f"Database error: {e}")
        return None
    
def get_lga_results(lga_id):
    try:
        conn = sqlite3.connect("data.sqlite")
        cursor = conn.cursor()
        
        query = """
        SELECT apr.party_abbreviation, SUM(apr.party_score) AS total_score
        FROM polling_unit pu
        JOIN announced_pu_results apr ON pu.uniqueid = apr.polling_unit_uniqueid
        WHERE pu.lga_id = ?
        GROUP BY apr.party_abbreviation;
        """
        
        cursor.execute(query, (lga_id,))
        results = cursor.fetchall()
        
        conn.close()
        return results
    except Exception as e:
        print(f"Database error: {e}")
        return None
    
def store_polling_unit_results(polling_unit_id, party_results):
    try:
        conn = sqlite3.connect("data.sqlite")
        cursor = conn.cursor()
        
        for party, score in party_results.items():
            query = """
            INSERT INTO announced_pu_results (polling_unit_uniqueid, party_abbreviation, party_score)
            VALUES (?, ?, ?);
            """
            cursor.execute(query, (polling_unit_id, party, score))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database Error: {e}")
        return False
    
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.show_form()
        elif self.path.startswith("/results"):
            self.show_polling_unit_results()
        elif self.path.startswith("/lga-results"):
            self.show_lga_results()
        elif self.path.startswith("/add-polling-unit"):
            self.show_add_polling_unit_form()
        elif self.path.startswith("/save-polling-unit"):
            self.save_polling_unit_results()
        
    def show_form(self):
        # Generate the HTML form
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Polling Unit and LGA Results</title></head>
        <body>
            <h1>Polling Unit and LGA Results Viewer</h1>
            <form action="/results" method="get">
                <label for="polling_unit_id">Enter Polling Unit ID:</label>
                <input type="text" id="polling_unit_id" name="polling_unit_id" required>
                <button type="submit">Get Polling Unit Results</button>
            </form>
            <br>
            <form action="/lga-results" method="get">
                <label for="lga_id">Enter LGA ID:</label>
                <input type="text" id="lga_id" name="lga_id" required>
                <button type="submit">Get LGA Results</button>
            </form>
            <br>
            <a href="/add-polling-unit">
                <button>Add New Polling Unit Results</button>
            </a>
        </body>
        </html>
        """
        self.respond(html)
        
    def show_polling_unit_results(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        polling_unit_id = params.get("polling_unit_id", [None])[0]

        if not polling_unit_id:
            self.show_form()
            return

        results = get_polling_unit_results(polling_unit_id)
        
        if results:
            rows = "".join(
                f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
                for row in results
            )
            results_html = f"""
            <h2>Results for Polling Unit ID: {polling_unit_id}</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Polling Unit ID</th>
                        <th>Polling Unit Name</th>
                        <th>Party</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        else:
            results_html = f"<h2>No results found for Polling Unit ID: {polling_unit_id}</h2>"
            
        results_html += '<br><a href="/">Back to form</a>'
        self.respond(f"<!DOCTYPE html><html><body>{results_html}</body></html>")
        
    def show_lga_results(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        lga_id = params.get("lga_id", [None])[0]

        if not lga_id:
            self.show_form()
            return

        results = get_lga_results(lga_id)

        if results:
            rows = "".join(
                f"<tr><td>{row[0]}</td><td>{row[1]}</td></tr>"
                for row in results
            )
            results_html = f"""
            <h2>Summed Results for LGA ID: {lga_id}</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Party</th>
                        <th>Total Score</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        else:
            results_html = f"<h2>No results found for LGA ID: {lga_id}</h2>"

        results_html += '<br><a href="/">Back to form</a>'
        self.respond(f"<!DOCTYPE html><html><body>{results_html}</body></html>")
        
    def show_add_polling_unit_form(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Add Polling Unit Results</title></head>
        <body>
            <h1>Add Polling Unit Results</h1>
            <form action="/save-polling-unit" method="post">
                <label for="polling_unit_id">Polling Unit ID:</label>
                <input type="text" id="polling_unit_id" name="polling_unit_id" required><br><br>
            
                <label for="party_results">Enter Party Results (Format: PartyAbbreviation=Score, separated by commas):</label><br>
                <textarea id="party_results" name="party_results" rows="5" cols="40" required></textarea><br><br>
            
                <button type="submit">Save Results</button>
            </form>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
        
    def save_polling_unit_results(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        data = urllib.parse.parse_qs(post_data)
        
        polling_unit_id = data.get("polling_unit_id", [None])[0]
        party_results_raw = data.get("party_results", [""])[0]
        
        party_results = {}
        for item in party_results_raw.split(","):
            if "=" in item:
                party, score = item.split("=")
                party_results[party.strip()] = int(score.strip())
                
        if store_polling_unit_results(polling_unit_id, party_results):
            message = "Results successfully saved!"
        else:
            message = "An error occurred while saving results."
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Save Results</title></head>
        <body>
            <h1>{message}</h1>
            <a href="/">Go back to Home</a>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
        
    def respond(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
        
def run_server():
    print("Starting server at http://localhost:8000...")
    server = HTTPServer(("localhost", 8000), RequestHandler)
    server.serve_forever()
    
if __name__ == "__main__":
    run_server()