from http.server import BaseHTTPRequestHandler
import sys
import os

# Add the root directory to sys.path so we can import from main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import RubinAgent

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print("Vercel Cron triggered Rubin Agent")
            
            agent = RubinAgent(
                config_path="config.json", 
                system_prompt_path="system_prompt.md", 
                seeds_path="seeds.json"
            )
            
            # Note: Serverless environments have low timeouts (e.g. 10s on Vercel Hobby).
            # We don't use jitter/sleep here.
            thought = agent.run_once()
            
            if thought:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Executed single run successfully. Thought length: {len(thought)}".encode('utf-8'))
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Error: Failed to generate thought.")
                
        except Exception as e:
            print(f"Error in Vercel Cron execution: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
