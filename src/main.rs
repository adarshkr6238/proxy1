use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt, copy_bidirectional};
use std::env;
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let port = env::var("PORT").unwrap_or_else(|_| "7860".to_string());
    let listen_addr = format!("0.0.0.0:{}", port);
    
    let listener = TcpListener::bind(&listen_addr).await?;
    println!("Listening on {}", listen_addr);

    loop {
        let (mut client_stream, _) = listener.accept().await?;
        tokio::spawn(async move {
            if let Err(e) = handle_client(client_stream).await {
                eprintln!("Error handling client: {:?}", e);
            }
        });
    }
}

async fn handle_client(mut client_stream: TcpStream) -> Result<(), Box<dyn Error>> {
    let mut buffer = [0; 1024];
    let n = client_stream.read(&mut buffer).await?;
    if n == 0 { return Ok(()); }
    
    let request = String::from_utf8_lossy(&buffer[..n]);

    if request.starts_with("CONNECT") {
        let parts: Vec<&str> = request.split_whitespace().collect();
        if parts.len() < 2 { return Err("Invalid CONNECT request".into()); }
        let target = parts[1];
        println!("CONNECT to {}", target);

        let mut target_stream = TcpStream::connect(target).await?;
        client_stream.write_all(b"HTTP/1.1 200 Connection Established\r\n\r\n").await?;
        copy_bidirectional(&mut client_stream, &mut target_stream).await?;
    }
    Ok(())
}
